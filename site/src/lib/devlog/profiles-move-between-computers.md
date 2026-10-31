Setting up a profile takes a while: the place, the price and size, the dispositions, the preferences, and which places nearby matter. Until now there was no way to take that to another computer except building every profile again by hand. Now a new menu next to the profile tabs saves the chosen profiles into a file and adds the profiles from such a file. It was the last feature for version 0.3.0.

## Saving and opening

The menu opens a window listing every profile, all ticked. Unticking some leaves them out. The system's own Save dialog then asks where the file goes. Importing works the other way round: the system's Open dialog picks the file, the app adds every profile in it, and a short report lists what was added and what could not be.

The app is built with Tauri, a toolkit for desktop apps whose window is a web page. The window cannot touch files on its own, so the Tauri shell around it shows the dialogs and reads or writes the file. The shell only moves the text. What a profile looks like in the file is decided by the window, so the format can change without touching the Rust side.

## What the file holds

The file is plain JSON. Each profile in it is exactly what the engine needs to create it again, its search, its preferences and its portals, plus the kinds of place it shows nearby on the map. Places are saved by their code in RÚIAN, the Czech state register of addresses and places, so a place means the same place on every computer, whatever it is called.

The file never holds listings. The flats a profile found, its favourites and its price history stay on the computer that found them. That keeps the file small and keeps listing data from being passed around. A paused profile also comes in running, since on a new computer you most likely want it scanning.

The file carries a version number. A file of a later format is refused rather than misread.

## Importing always adds

A profile from the file never replaces or merges into one already there. It is created through the engine's own FastAPI endpoint, the same one the profile editor uses, so the engine checks it just as it would a profile made by hand. When its name is taken, it gets the next free number. A file imported twice gives "Praha (3)", not "Praha (2) (2)".

If the engine refuses a profile, for example because a place in it does not exist, the report names it and the others still come in.

## Reading carefully

A JSON file can hold anything, so the app reads every field by name and checks its type. A file it did not write, or one edited into something it cannot read, is refused as a whole rather than half read. Some editors put an invisible byte order mark at the start of a file, and such a file still reads fine.

Reading every field by name has a second use. The panel's TypeScript types come from the engine's OpenAPI description, so when the engine's idea of a profile changes, the reader stops compiling right there, instead of imports quietly failing for users later.

## Two small bugs

A quick double click could open two dialogs and import the same file twice. The dialogs now block the window while they are open, and the window stays blocked until the import is done.

Placed among the profile tabs, the new menu was clipped by the tabs' sideways scrolling. It now sits just after them.

## Version 0.3.0

This and the updater make version 0.3.0. The first release build failed, because the updater's HTTPS libraries are under the ISC license, which the release's license check did not know yet. ISC is a short permissive license, like MIT, so it is now accepted, and the release built on all three systems.

If you are on 0.2.0, installing 0.3.0 over it keeps all your data, since the app keeps the same data folder. The profiles file is for moving to another computer. From 0.3.0 on, the app will offer new versions itself.
