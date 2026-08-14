# NOMAD Music — WebView2 Runtime

NOMAD Music is a Tauri desktop application and uses Microsoft's WebView2 runtime on Windows.

## End users

The NSIS installer is configured with Tauri's **embedded Evergreen Bootstrapper** mode. The installer checks for WebView2 and installs it when necessary; the application therefore does not require the user to manually install WebView2 first. Tauri documents `embedBootstrapper` as the online installer mode that embeds a small bootstrapper; the bootstrapper then obtains the appropriate Evergreen runtime from Microsoft.

The first installation therefore needs internet access. For fully offline enterprise deployment, the project can later switch to Tauri's `offlineInstaller` mode, which embeds the larger Evergreen standalone installer.

## Developer machine

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\setup-windows.ps1
```

The setup script detects WebView2 through the Windows Edge Update registry locations / installation paths. When missing, it downloads Microsoft's official Evergreen Bootstrapper and runs it silently with:

```text
/silent /install
```

Microsoft documents the Evergreen Bootstrapper as a small installer that downloads the matching runtime and installs it, and documents the silent installation command.

## Important

You do **not** need Microsoft Edge itself as the user-facing browser dependency. NOMAD uses WebView2 as its embedded web runtime. Tauri documents WebView2 as the Windows rendering runtime for Tauri applications.
