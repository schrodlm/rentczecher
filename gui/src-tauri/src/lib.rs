use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{mpsc, Mutex};
use std::thread;
use std::time::Duration;

use tauri::{Manager, RunEvent};

// How long the engine may take to announce its port before the shell gives up.
const PORT_ANNOUNCE_TIMEOUT: Duration = Duration::from_secs(10);

// The origin the window's page runs on in a debug build, served by Vite.
const DEV_WINDOW_ORIGIN: &str = "http://localhost:5173";

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
}

#[tauri::command]
fn sidecar_connection(sidecar: tauri::State<'_, Sidecar>) -> SidecarConnection {
    sidecar.connection.clone()
}

/// A fresh secret for every launch, 32 bytes from the OS random source as hex.
fn generate_token() -> String {
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes).expect("the OS random source is unavailable");
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// A debug build runs the engine from source, so engine edits show on the
/// next launch without re-freezing.
#[cfg(debug_assertions)]
fn engine_command() -> Command {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let mut command = Command::new("uv");
    command.args(["run", "rentczecher", "serve"]).current_dir(repo);
    command
}

fn start_engine() -> Result<Sidecar, String> {
    let token = generate_token();
    let mut command = engine_command();
    command
        .args(["--port", "0", "--allow-origin", DEV_WINDOW_ORIGIN])
        .env("RENTCZECHER_API_TOKEN", &token)
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

    // The reader keeps draining stdout after the PORT line. A pipe nobody
    // reads fills up, and the engine would then block on its next print.
    let stdout = process.stdout.take().expect("stdout was piped");
    let (port_sender, port_receiver) = mpsc::channel();
    thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            match line.strip_prefix("PORT=") {
                Some(port) => {
                    let _ = port_sender.send(port.to_string());
                }
                None => log::info!("engine: {line}"),
            }
        }
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
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            app.manage(start_engine()?);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![sidecar_connection])
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
