Until now an installed app never learned that a newer version existed. Everyone would have stayed on the version they first installed, unless they came back to the website to check. Now the app can update itself. When a newer release is out, the top bar says so, and one click downloads it, checks that it really comes from me, installs it and restarts into the new version.

## Asking for a new version

The app is built with Tauri, a toolkit for desktop apps whose window is a web page. Tauri has an updater plugin, and the app uses it. When the app starts and once a day after that, it fetches a small JSON file from the newest GitHub Release. The file names the latest version and, for each kind of installer, where to download it and its signature. If the version is newer than the one running, the top bar shows it with an "Update and restart" button. Without internet the app simply tries again next time.

The app only offers the update. Nothing is downloaded until you click, so a scan is never cut short by a restart. A build I am working on never checks, because it would offer to replace itself with the last release.

## Why every release is signed

HTTPS proves that a file came from GitHub. It does not prove that I put it there. Anyone who got hold of the release, or of the account, could offer a different program, and the app would install it.

So every release is now signed. The build signs each file the app can update from with a private key that only the build has, kept as a GitHub Actions secret. The app carries the matching public key and refuses any download the key did not sign.

The signature also covers the version number. Without that, someone able to fake the update file could offer an old release under a new number and push people back to a version with known bugs. No release before this one was signed, so requiring it costs nothing.

The key is a one-way door. Every app installed from now on trusts this key and only this key. If I lose it, those apps can never be updated again, so its backup lives outside GitHub.

## The release writes the update file

After the installers for Windows, macOS and Linux are built and signed, a small Python script gathers them and their signatures into the update file and attaches it to the release. It stops the release if any installer or signature is missing.

It also checks which key signed each one. The build only warns when it signs with a different key than the app trusts, and the result is a release no installed app would accept. The script turns that warning into a failed release.

A release still starts as a draft, and GitHub does not count drafts as the latest release. So no app is offered a version until I have tried it and published it.

## Three systems, three kinds of installer

"Installer" means something different on each system. Windows runs a real setup program. On macOS the update is not the disk image people download but a packed copy of the app itself, which the release now ships as well. The Linux AppImage just replaces itself, and the Debian package goes through the system's package manager and asks for a password.

Windows had one surprise. There the updater launches the installer and then ends the app at once, past the normal shutdown that would stop the engine, the Python process that does the scanning. The installer cannot replace files that are still in use, so the app now stops the engine right before that exit, and waits until it has really gone.

## The privacy policy

Checking for updates is a new connection, so the privacy policy now names GitHub, what the app asks it and when. GitHub counts each check and download, so I can see how often apps check, but not who checked.

## Next

Updating can only be proven with two signed releases: install the first, publish the second, and see each system offer it and update. Version 0.3.0 is the first one.
