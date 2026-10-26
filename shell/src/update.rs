use std::sync::{Mutex, MutexGuard, PoisonError};

use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_updater::{Update, UpdaterExt};

use crate::Sidecar;

// The event the window receives while an update downloads. The panel's
// onUpdateProgress() listens for exactly this name.
const UPDATE_PROGRESS_EVENT: &str = "update-progress";

/// How far the download of an update has come, in whole percent, or None
/// while the server has not said how large the update is.
#[derive(Clone, serde::Serialize)]
struct UpdateProgress {
    percent: Option<u64>,
}

/// None while the size is unknown. A server that sends more than it announced
/// never shows past 100.
fn percent_of(downloaded: u64, total: Option<u64>) -> Option<u64> {
    total
        .filter(|total| *total > 0)
        .map(|total| (downloaded.saturating_mul(100) / total).min(100))
}

/// Where the app stands with updating: nothing found yet, an update found by
/// the last check, or one being installed.
#[derive(Default)]
enum UpdateStage {
    #[default]
    Idle,
    Found(Box<Update>),
    Installing,
}

#[derive(Default)]
pub(crate) struct PendingUpdate(Mutex<UpdateStage>);

impl PendingUpdate {
    // Nothing panics while holding the stage, so a poisoned lock still
    // holds a sound one.
    fn stage(&self) -> MutexGuard<'_, UpdateStage> {
        self.0.lock().unwrap_or_else(PoisonError::into_inner)
    }
}

/// Asks the release server for a newer release and returns its version. A
/// development build never offers a release in place of itself, and no check
/// runs while an update installs.
#[tauri::command]
pub(crate) async fn check_for_update(app: AppHandle, pending: State<'_, PendingUpdate>) -> Result<Option<String>, String> {
    if cfg!(debug_assertions) {
        return Ok(None);
    }
    if matches!(*pending.stage(), UpdateStage::Installing) {
        return Err("an update is installing".to_string());
    }
    // On Windows the installer replaces the app's files, the engine's among
    // them, and a running program's files cannot be replaced there. The
    // updater ends the app abruptly before the installer starts, past the
    // shutdown that would stop the engine, so the engine stops here first.
    // The hook stands in for the updater's own, which only cleans up.
    let app_handle = app.clone();
    let updater = app
        .updater_builder()
        .on_before_exit(move || {
            if let Some(sidecar) = app_handle.try_state::<Sidecar>() {
                sidecar.stop();
            }
            app_handle.cleanup_before_exit();
        })
        .build()
        .map_err(|error| error.to_string())?;
    let found = updater.check().await.map_err(|error| {
        log::warn!("could not check for an update: {error}");
        error.to_string()
    })?;
    let version = found.as_ref().map(|update| update.version.clone());
    let mut stage = pending.stage();
    // An install may have begun while the check was waiting on the server.
    if !matches!(*stage, UpdateStage::Installing) {
        *stage = match found {
            Some(update) => UpdateStage::Found(Box::new(update)),
            None => UpdateStage::Idle,
        };
    }
    Ok(version)
}

/// Downloads and installs the update the last check found, then starts the
/// new version. On Windows the installer starts it, and the app ends as soon
/// as the installer runs. A failed install is let go of, and the next check
/// finds the update again.
#[tauri::command]
pub(crate) async fn install_update(app: AppHandle, pending: State<'_, PendingUpdate>) -> Result<(), String> {
    let update = {
        let mut stage = pending.stage();
        match std::mem::take(&mut *stage) {
            UpdateStage::Found(update) => {
                *stage = UpdateStage::Installing;
                *update
            }
            UpdateStage::Installing => {
                *stage = UpdateStage::Installing;
                return Err("an update is already installing".to_string());
            }
            UpdateStage::Idle => return Err("no update to install, check for one first".to_string()),
        }
    };
    log::info!("installing version {}", update.version);
    let mut downloaded: u64 = 0;
    let mut last_percent = None;
    let installed = update
        .download_and_install(
            |chunk, total| {
                downloaded += chunk as u64;
                let percent = percent_of(downloaded, total);
                if percent != last_percent {
                    last_percent = percent;
                    let _ = app.emit(UPDATE_PROGRESS_EVENT, UpdateProgress { percent });
                }
            },
            || log::info!("downloaded the update"),
        )
        .await;
    if let Err(error) = installed {
        log::error!("could not install the update: {error}");
        *pending.stage() = UpdateStage::Idle;
        return Err(error.to_string());
    }
    app.restart();
}
