use std::fs;
use std::io::{BufRead, BufReader, ErrorKind};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{mpsc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{Emitter, Manager, RunEvent};
use tauri_plugin_dialog::{DialogExt, MessageDialogKind};

// The event the window receives when the engine's process ends. The panel's
// onEngineStopped() listens for exactly this name.
const ENGINE_STOPPED_EVENT: &str = "engine-stopped";

// How long the engine may take to announce its port before the shell gives up.
const PORT_ANNOUNCE_TIMEOUT: Duration = Duration::from_secs(10);

// How long the engine may take, after announcing its port, to answer its
// health check, and how often the shell asks.
const HEALTH_TIMEOUT: Duration = Duration::from_secs(10);
const HEALTH_POLL_INTERVAL: Duration = Duration::from_millis(250);

// The origins the window's page runs on. A debug build loads it from Vite, a
// release build from inside the app, whose origin differs on Windows.
#[cfg(debug_assertions)]
const WINDOW_ORIGINS: &[&str] = &["http://localhost:5173"];
#[cfg(not(debug_assertions))]
const WINDOW_ORIGINS: &[&str] = &["tauri://localhost", "http://tauri.localhost"];

/// Where the engine listens and the token it expects. The panel's
/// sidecarConnection() reads exactly these two camelCase fields.
#[derive(Clone, serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct SidecarConnection {
    base_url: String,
    token: String,
}

/// The engine process the shell started, and how to reach it.
struct Sidecar {
    connection: SidecarConnection,
    process: Mutex<Child>,
    // The write end of the engine's stdin, never written to. The engine runs
    // with --exit-with-parent, so when this shell dies for any reason the OS
    // closes the pipe and the engine shuts itself down.
    _parent_link: ChildStdin,
}

/// The file holding the user config. The panel owns its shape, the shell only
/// moves its text.
struct UserConfigFile(PathBuf);

impl UserConfigFile {
    fn in_folder(folder: &Path) -> UserConfigFile {
        UserConfigFile(folder.join("user_config.json"))
    }
}

/// The user config as written, or None while it does not exist yet.
#[tauri::command]
fn read_user_config(file: tauri::State<'_, UserConfigFile>) -> Result<Option<String>, String> {
    match fs::read_to_string(&file.0) {
        Ok(contents) => Ok(Some(contents)),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(None),
        Err(error) => Err(format!("could not read {}: {error}", file.0.display())),
    }
}

/// Replaces the user config. It is written beside the file and renamed over
/// it, so a crash midway never leaves half a file behind.
#[tauri::command]
fn write_user_config(file: tauri::State<'_, UserConfigFile>, contents: String) -> Result<(), String> {
    let path = &file.0;
    let folder = path.parent().ok_or_else(|| format!("{} has no folder", path.display()))?;
    fs::create_dir_all(folder).map_err(|error| format!("could not create {}: {error}", folder.display()))?;
    let unfinished = path.with_extension("json.unfinished");
    fs::write(&unfinished, contents).map_err(|error| format!("could not write {}: {error}", unfinished.display()))?;
    fs::rename(&unfinished, path).map_err(|error| format!("could not replace {}: {error}", path.display()))
}

/// The app's own folder in the OS config folder.
fn config_folder(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let os_folder = app
        .path()
        .config_dir()
        .map_err(|error| format!("could not locate the config folder: {error}"))?;
    Ok(os_folder.join("rentczecher"))
}

#[tauri::command]
fn sidecar_connection(sidecar: tauri::State<'_, Sidecar>) -> SidecarConnection {
    sidecar.connection.clone()
}

/// Opens a link to another site in the default browser, since the app's
/// window opens no windows of its own. Only https links, so the panel can
/// never make the shell open a file or run a program.
#[tauri::command]
fn open_in_browser(url: String) -> Result<(), String> {
    if !url.starts_with("https://") {
        return Err(format!("not an https link: {url}"));
    }
    open::that_detached(&url).map_err(|error| error.to_string())
}

/// A fresh secret for every launch, 32 bytes from the OS random source as hex.
fn generate_token() -> String {
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes).expect("the OS random source is unavailable");
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// The engine's source folder, which a debug build runs the engine from.
#[cfg(debug_assertions)]
fn engine_source() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../engine")
}

/// With RENTCZECHER_SCENARIO set, a debug build first replays that scenario
/// into a scratch folder and runs there, so development never touches the
/// real data or the real user config.
#[cfg(debug_assertions)]
fn scenario_home() -> Result<Option<PathBuf>, String> {
    match std::env::var("RENTCZECHER_SCENARIO") {
        Ok(scenario) => replay_scenario(&engine_source(), &scenario).map(Some),
        Err(_) => Ok(None),
    }
}

#[cfg(not(debug_assertions))]
fn scenario_home() -> Result<Option<PathBuf>, String> {
    Ok(None)
}

/// A debug build runs the engine from source, so engine edits show on the
/// next launch without re-freezing.
#[cfg(debug_assertions)]
fn engine_command(_app: &tauri::AppHandle, scenario_home: Option<&Path>) -> Result<Command, String> {
    let mut command = Command::new("uv");
    command.args(["run", "rentczecher", "serve"]).current_dir(engine_source());
    if let Some(home) = scenario_home {
        command.env("RENTCZECHER_DATA_DIR", home.join("data"));
    }
    Ok(command)
}

/// Replays the named scenario into a scratch folder of its own, replacing
/// any earlier replay, and returns that folder.
#[cfg(debug_assertions)]
fn replay_scenario(engine: &Path, scenario: &str) -> Result<PathBuf, String> {
    let home = std::env::temp_dir().join("rentczecher-scenarios").join(scenario);
    let status = Command::new("uv")
        .args(["run", "python", "-m", "tests.scenarios", scenario])
        .arg(&home)
        .current_dir(engine)
        .status()
        .map_err(|error| format!("could not replay scenario {scenario}: {error}"))?;
    if !status.success() {
        return Err(format!("scenario {scenario} did not replay, see the terminal for why"));
    }
    log::info!("running on scenario {scenario} in {}", home.display());
    Ok(home)
}

/// A release build runs the frozen engine the bundle ships as a resource.
#[cfg(not(debug_assertions))]
fn engine_command(app: &tauri::AppHandle, _scenario_home: Option<&Path>) -> Result<Command, String> {
    let executable = if cfg!(windows) { "rentczecher-sidecar.exe" } else { "rentczecher-sidecar" };
    let path = app
        .path()
        .resource_dir()
        .map_err(|error| format!("could not locate the app's resources: {error}"))?
        .join("sidecar")
        .join("rentczecher-sidecar")
        .join(executable);
    let mut command = Command::new(path);
    command.arg("serve");
    Ok(command)
}

fn start_engine(app: &tauri::AppHandle, scenario_home: Option<&Path>) -> Result<Sidecar, String> {
    let token = generate_token();
    let mut command = engine_command(app, scenario_home)?;
    command.args(["--port", "0", "--exit-with-parent"]);
    for origin in WINDOW_ORIGINS {
        command.args(["--allow-origin", origin]);
    }
    command
        .env("RENTCZECHER_API_TOKEN", &token)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped());
    #[cfg(windows)]
    {
        // Without this the engine opens its own console window on Windows.
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }
    let mut process = command
        .spawn()
        .map_err(|error| format!("could not start the engine: {error}"))?;

    let parent_link = process.stdin.take().expect("stdin was piped");

    // The reader keeps draining stdout after the PORT line. A pipe nobody
    // reads fills up, and the engine would then block on its next print.
    // The pipe closes when the engine's process ends, however it ends, so the
    // loop finishing is the shell's signal that the engine is gone.
    let stdout = process.stdout.take().expect("stdout was piped");
    let (port_sender, port_receiver) = mpsc::channel();
    let app_handle = app.clone();
    thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            match line.strip_prefix("PORT=") {
                Some(port) => {
                    let _ = port_sender.send(port.to_string());
                }
                None => log::info!("engine: {line}"),
            }
        }
        log::warn!("the engine stopped");
        let _ = app_handle.emit(ENGINE_STOPPED_EVENT, ());
    });

    let port = match port_receiver.recv_timeout(PORT_ANNOUNCE_TIMEOUT) {
        Ok(port) => port,
        Err(_) => {
            let _ = process.kill();
            return Err("the engine did not announce its port in time".to_string());
        }
    };
    Ok(Sidecar {
        connection: SidecarConnection {
            base_url: format!("http://127.0.0.1:{port}"),
            token,
        },
        process: Mutex::new(process),
        _parent_link: parent_link,
    })
}

/// Waits until the engine answers an authenticated health check. A bound
/// port only proves the socket exists, the answer proves the app behind it
/// is serving.
fn wait_for_health(connection: &SidecarConnection) -> Result<(), String> {
    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(HEALTH_POLL_INTERVAL))
        .build()
        .into();
    let url = format!("{}/v1/health", connection.base_url);
    let authorization = format!("Bearer {}", connection.token);
    let deadline = Instant::now() + HEALTH_TIMEOUT;
    while Instant::now() < deadline {
        if agent.get(&url).header("Authorization", &authorization).call().is_ok() {
            return Ok(());
        }
        thread::sleep(HEALTH_POLL_INTERVAL);
    }
    Err("the engine did not become healthy in time".to_string())
}

/// Starts the engine and waits until it is healthy, killing it again when it
/// never becomes healthy so no half-started engine is left behind.
fn start_healthy_engine(app: &tauri::AppHandle, scenario_home: Option<&Path>) -> Result<Sidecar, String> {
    let sidecar = start_engine(app, scenario_home)?;
    if let Err(error) = wait_for_health(&sidecar.connection) {
        if let Ok(mut process) = sidecar.process.lock() {
            let _ = process.kill();
        }
        return Err(error);
    }
    Ok(sidecar)
}

/// Tells the user startup failed, then exits once they dismiss the message.
/// The text is English, because the panel's translations load with the
/// window, and no window exists yet.
fn report_startup_failure(app: &tauri::AppHandle, error: &str) {
    log::error!("startup failed: {error}");
    let app_handle = app.clone();
    app.dialog()
        .message(format!("rentczecher could not start.\n\n{error}"))
        .title("rentczecher")
        .kind(MessageDialogKind::Error)
        .show(move |_| app_handle.exit(1));
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            let started = scenario_home().and_then(|home| {
                let user_config = match &home {
                    Some(home) => UserConfigFile::in_folder(home),
                    None => UserConfigFile::in_folder(&config_folder(app.handle())?),
                };
                let sidecar = start_healthy_engine(app.handle(), home.as_deref())?;
                Ok((user_config, sidecar))
            });
            let (user_config, sidecar) = match started {
                Ok(started) => started,
                Err(error) => {
                    // No window opens. The dialog's callback ends the app.
                    report_startup_failure(app.handle(), &error);
                    return Ok(());
                }
            };
            app.manage(user_config);
            app.manage(sidecar);

            // The window is declared in tauri.conf.json but created only now,
            // so the panel never loads before the engine can answer it.
            let window_config = app
                .config()
                .app
                .windows
                .first()
                .ok_or("tauri.conf.json declares no window")?
                .clone();
            tauri::WebviewWindowBuilder::from_config(app.handle(), &window_config)?.build()?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            sidecar_connection,
            open_in_browser,
            read_user_config,
            write_user_config
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            // Graceful shutdown comes with the lifecycle work, for now the
            // engine only must not outlive the app.
            if let RunEvent::Exit = event
                && let Some(sidecar) = app.try_state::<Sidecar>()
                && let Ok(mut process) = sidecar.process.lock()
            {
                let _ = process.kill();
            }
        });
}
