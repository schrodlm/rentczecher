use std::fs;

use tauri::WebviewWindow;
use tauri_plugin_dialog::DialogExt;

const SUGGESTED_FILE_NAME: &str = "rentczecher-profiles.json";

// A file of profiles holds a few kilobytes. The cap stops a wrongly picked
// large file from being read whole and sent to the window.
const MAX_FILE_BYTES: u64 = 1_000_000;

/// Asks where to save the profiles the panel wrote, then saves them there.
/// False when the user closed the dialog without choosing. The panel owns the
/// file's shape, the shell only moves its text.
#[tauri::command]
pub(crate) async fn save_profiles_file(window: WebviewWindow, contents: String) -> Result<bool, String> {
    let chosen = window
        .dialog()
        .file()
        // Modal to the window, so the window cannot open a second dialog.
        .set_parent(&window)
        .add_filter("JSON", &["json"])
        .set_file_name(SUGGESTED_FILE_NAME)
        .blocking_save_file();
    let Some(chosen) = chosen else {
        return Ok(false);
    };
    let path = chosen.into_path().map_err(|error| error.to_string())?;
    fs::write(&path, contents).map_err(|error| format!("could not write {}: {error}", path.display()))?;
    Ok(true)
}

/// Asks for a file of profiles and returns its text, or None when the user
/// closed the dialog without choosing.
#[tauri::command]
pub(crate) async fn open_profiles_file(window: WebviewWindow) -> Result<Option<String>, String> {
    let chosen = window
        .dialog()
        .file()
        // Modal to the window, so the window cannot open a second dialog.
        .set_parent(&window)
        .add_filter("JSON", &["json"])
        .blocking_pick_file();
    let Some(chosen) = chosen else {
        return Ok(None);
    };
    let path = chosen.into_path().map_err(|error| error.to_string())?;
    let size = fs::metadata(&path)
        .map_err(|error| format!("could not read {}: {error}", path.display()))?
        .len();
    if size > MAX_FILE_BYTES {
        return Err(format!("{} is too large to be a file of profiles", path.display()));
    }
    fs::read_to_string(&path)
        .map(Some)
        .map_err(|error| format!("could not read {}: {error}", path.display()))
}
