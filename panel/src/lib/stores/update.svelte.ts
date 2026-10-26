import { invoke } from '@tauri-apps/api/core';
import { listen, type UnlistenFn } from '@tauri-apps/api/event';
import { errorMessage } from '$lib/errors';

export type UpdateState =
	| { status: 'none' }
	| { status: 'available'; version: string }
	| { status: 'installing'; version: string; percent: number | null }
	| { status: 'failed'; version: string; error: string };

// A running app looks again once a day, so one left open for weeks still
// hears of a release.
export const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;

const RELEASES_URL = 'https://github.com/schrodlm/rentczecher/releases/tag';

/* The page where a release can be downloaded by hand, for when installing it
from the app fails. */
export function releasePage(version: string): string {
	return `${RELEASES_URL}/v${version}`;
}

/* Calls onprogress with how far an update's download has come, in whole
percent, or null while its size is unknown. The shell emits exactly this
event name. */
export function onUpdateProgress(onprogress: (percent: number | null) => void): Promise<UnlistenFn> {
	return listen<{ percent: number | null }>('update-progress', (event) => onprogress(event.payload.percent));
}

/* Whether a newer release exists, and installing it. A check that fails,
as it does offline, leaves the state as it was: the shell has logged why,
and the next check tries again. */
export class UpdateStore {
	state = $state<UpdateState>({ status: 'none' });
	private timer: ReturnType<typeof setInterval> | null = null;

	watch(): void {
		this.unwatch();
		void this.check();
		this.timer = setInterval(() => void this.check(), CHECK_INTERVAL_MS);
	}

	unwatch(): void {
		if (this.timer !== null) clearInterval(this.timer);
		this.timer = null;
	}

	async check(): Promise<void> {
		if (this.installing()) return;
		let version: string | null;
		try {
			version = await invoke<string | null>('check_for_update');
		} catch {
			return;
		}
		// An install may have begun while the check was waiting on the shell.
		if (this.installing()) return;
		this.state = version === null ? { status: 'none' } : { status: 'available', version };
	}

	private installing(): boolean {
		return this.state.status === 'installing';
	}

	/* Resolves only when installing fails. Otherwise the app restarts into
	the new version before it could. A failed install is offered again only
	after the next check, since the shell lets go of the update it tried. */
	async install(): Promise<void> {
		if (this.state.status !== 'available') return;
		const version = this.state.version;
		this.state = { status: 'installing', version, percent: null };
		let unlisten: UnlistenFn | null = null;
		try {
			unlisten = await onUpdateProgress((percent) => {
				if (this.state.status === 'installing') this.state = { ...this.state, percent };
			});
			await invoke('install_update');
		} catch (error) {
			this.state = { status: 'failed', version, error: errorMessage(error) };
		} finally {
			unlisten?.();
		}
	}
}
