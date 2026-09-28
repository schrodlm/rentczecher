// Without this, release builds on Windows open a console window beside the app.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
  rentczecher_lib::run();
}
