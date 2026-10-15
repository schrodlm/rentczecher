This step had two parts. I cleaned up how the repository is organised, and I got the app building on Linux, Windows and macOS. The second part was the last thing missing for the desktop app milestone.

## Decisions written down

I started the project with a planning folder I wrote in July. By October a lot of it no longer matched what I had actually built. I went through it and kept only the decisions that still hold, each as an Architecture Decision Record. That is a short document in the repository describing one decision and why I made it. There are records for things like the desktop app being a Tauri shell around a Python engine, duplicate detection comparing listings in pairs, and place data being resolved offline. The rest of the folder became regular docs and issues, and I deleted it.

## Three parts, side by side

The repository now has three folders: `engine/` for the Python engine, `panel/` for the SvelteKit screens and `shell/` for the Rust desktop wrapper. I put the shell next to the panel and not inside it, because most of what the shell does is about running the engine, not about the screens.

I wanted every moved file to keep its history. Git does not actually store that a file was moved. It works it out afterwards by comparing how similar the contents are. So I made the moves in commits that only move files and change nothing else. That way `git log` and `git blame` still follow a file across the move.

I also sorted the tests by what they need to run. Most tests run offline. Tests that talk to the real portals, and tests that need the packaged engine, each have their own folder, and the folder marks them automatically.

## Building on three systems

GitHub Actions now builds the installers on three machines, one for each operating system. It has to be three, because PyInstaller, the tool that packages the Python engine, can only build for the system it runs on. After the build, a few smoke tests start the packaged engine and check that it ships its data, answers a health check, returns profiles and shuts down when the app closes its input.

A full run takes about 25 minutes, so I only run it for release tags and for one test branch.

## What went wrong on the way

The first Windows run failed right away. Python on Windows reads text files as Windows-1252 unless you tell it otherwise, so the Czech place names crashed the engine and the config was read wrong. I changed the engine to always read files as UTF-8.

Each system also bundled a different Python version. On Linux it took the machine's Python 3.10, which is missing a library the engine needs. I set the engine to require 3.11 and pinned 3.12, so all three installers now ship the same version.

The very first smoke test failed with "connection refused". The engine opens its port a moment before it is ready to answer, so I made the test retry the health check until it gets a reply. The app already did the same.

In the end all three systems built and passed, so I closed the milestone. Trying the real app on Windows and macOS is still waiting for testers.
