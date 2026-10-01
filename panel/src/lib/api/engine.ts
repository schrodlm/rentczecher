import { listen, type UnlistenFn } from '@tauri-apps/api/event';

/* Calls onstopped when the shell reports that the engine's process ended.
The shell emits exactly this event name when the engine's output pipe
closes. */
export function onEngineStopped(onstopped: () => void): Promise<UnlistenFn> {
	return listen('engine-stopped', () => onstopped());
}
