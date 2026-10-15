The app can now be light or dark and speak Czech or English, by your choice. The first time you launch it, a welcome wizard asks for both, then shows a short tour of what a profile does before you create your first one. After that, the top bar has a light/dark switch and a CS/EN switch.

## Where the choices live

The choices are saved in a small settings file, `user_config.json`, in the system's settings folder. The desktop app keeps it, not the engine. That matters for later: when the engine runs on a server and several devices connect to it, each of them should keep its own language and theme. If the file does not exist, the app has never been set up, and the wizard shows. The file is only written when the wizard finishes, so quitting halfway brings the wizard back next time.

The panel cannot read files itself, because it runs in the sandbox of a web page. It asks the Tauri shell by name, through a command, and the shell fills in the parts it manages on its own, like where the file is. Tauri also requires every command to be allowed explicitly, one at a time. So the panel can never choose which file it reads.

## Language is more than words

Switching to English is not just the strings. Numbers and dates follow the language too, through the browser's built-in `toLocaleString` formatting: 24 000 Kč in Czech, 24,000 Kč in English. English writes dates the British way, day before month, which suits a European app. Prices stay in Kč.

Changing the language reloads the app. To make that feel smooth, it reopens on the same profile and listing, which it remembers in `sessionStorage`. That storage survives a reload but not closing the window, which is exactly what this needs.

## The wizard

The wizard is a rounded card over the dimmed app, in three steps. First the language, picked by its flag. I drew the flags by hand, because emoji flags do not show on Windows. Then the theme, with a small preview of each. Then four slides of a profile at work, built from the app's own map, listing rows, score ring and price chart. "Create profile" opens the editor straight away, and "Later" is always there.

My first version let the wizard switch its own language and only reloaded the app at the end. That needed extra bookkeeping to remember things like "open the editor" across the reload. Reloading right when you pick a language, and passing the wizard's choices so far along in the address, removed all of it.

## A switch should always do something

The theme can follow the system, and that is the wizard's default. But the switch in the top bar only toggles light and dark. If you click a switch, you should see a change, and "follow the system" often looks exactly like what you already had.
