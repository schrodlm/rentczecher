# 3. The sidecar ships as a PyInstaller folder bundle

Status: accepted (2026-09-28)

## Context

The desktop app runs the engine as a frozen Python sidecar that users never
install Python for. PyInstaller freezes in two modes. One-file mode produces a
single executable, which is what Tauri's externalBin mechanism expects. It
unpacks its whole payload into a temporary folder on every launch. Folder mode
produces an executable beside an _internal/ directory and starts without
unpacking, but externalBin accepts only single files.

## Decision

The sidecar is frozen in folder mode and shipped as a bundle resource. The
shell resolves its path through Tauri's resource directory and starts it by
path, instead of through the one-line externalBin sidecar call. The first
build on Linux measured 73 MB, with the port announced 0.9 s after start.

## Consequences

- No unpacking on launch, so startup stays fast on slow disks and under
  antivirus scanning.
- Avoids a known trigger for false-positive antivirus warnings on Windows,
  where self-unpacking executables are flagged. For non-technical users that
  warning reads as "the app is a virus".
- The shell carries a few more lines: resource configuration and a path
  lookup, instead of Tauri's paved sidecar path.
- The freeze must run natively on each OS, one CI runner per platform, since
  PyInstaller cannot cross-compile.
