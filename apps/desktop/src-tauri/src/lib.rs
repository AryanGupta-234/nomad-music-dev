#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::time::Duration;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

#[tauri::command]
fn app_name() -> &'static str {
    "NOMAD Music"
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![app_name])
        .setup(|app| {
            #[cfg(not(debug_assertions))]
            {
                let sidecar = app
                    .shell()
                    .sidecar("nomad-server")
                    .expect("nomad-server sidecar must be bundled")
                    .args(["--host", "127.0.0.1", "--port", "8765"])
                    .spawn()
                    .expect("failed to start NOMAD server");

                app.manage(sidecar);
            }

            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_title("NOMAD Music");
            }

            // Small startup grace period. The UI also polls /health, so this is
            // only to avoid an immediate burst of failed requests.
            std::thread::sleep(Duration::from_millis(100));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running NOMAD Music");
}
