Before building features, I re-cut the road to a first release into seven milestones: the desktop app, profiles, a background watchdog, photos, a first-run setup, an installable release and a mode without a window. Then I started with the one most likely to fail. If a packaged Python engine could not run inside a desktop app, everything after it would need a different plan. So that had to be proven first.

## What Tauri actually is

The desktop app is built with Tauri. It took me a moment to see what that means. Tauri is a Rust library for a small native host program. The host opens a real window and shows the panel inside it, using the operating system's own browser engine instead of shipping a whole browser the way Electron does. Tauri's command-line tool only drives the build. The Rust compiler builds the host with the library inside.

The panel cannot be its own host. Web page code runs locked in a sandbox and cannot open windows or start processes. Something native has to come first and host it, a bit like firmware hosting a Lua interpreter.

## Packaging Python is not compiling it

The engine is Python, and users should not have to install Python. PyInstaller solves that, but not by compiling anything. The bundle it builds holds a small launcher, a Python interpreter, the code and its data files. Mine came out as a 73 MB folder that runs on a machine with no Python and answers in under a second.

It ships as a folder rather than a single file on purpose. A single-file bundle unpacks itself on every start, which is slower and tends to trip antivirus on Windows. And PyInstaller cannot build for another operating system, so each OS needs its own build machine.

## Starting the engine from the window

The app now does the whole startup itself. It generates a secret token, starts the engine with `--port 0` so the operating system picks any free port, reads back which port it got, and polls the engine's health check. Only when the engine answers does the window appear.

That last part needed a fight. Tauri normally builds its windows at startup, at the same moment the engine is still starting, so the panel loaded too early and found nothing to talk to. The fix was to stop Tauri creating the window and create it myself after the health check.

## A shutdown that never finished

Shutting the engine down cleanly exposed an old bug. The Server-Sent Events stream only noticed it should stop when it sent something, and a quiet stream never sent anything. Every closed tab had been leaking a worker thread since the API landed. Now the stream sends an SSE comment, a line browsers silently ignore, every second, so it always gets a chance to notice.

## Killing the wrong process, twice

Testing crash behaviour, I killed the engine by name, and twice it was the wrong process. The Python launcher starts two processes, and my search by name also matched my own command. Killing by the exact process ID worked. That crash handling became the next step.
