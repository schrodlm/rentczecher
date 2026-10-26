import { afterEach, describe, expect, test, vi } from 'vitest';

const shell = vi.hoisted(() => ({
	check: (async () => null) as () => Promise<unknown>,
	install: (async () => {}) as (progress: (percent: number | null) => void) => Promise<void>,
	progressListener: null as ((event: { payload: { percent: number | null } }) => void) | null,
	unlistened: 0
}));

vi.mock('@tauri-apps/api/core', () => ({
	invoke: async (command: string) => {
		if (command === 'check_for_update') return shell.check();
		if (command === 'install_update')
			return shell.install((percent) => shell.progressListener?.({ payload: { percent } }));
		throw new Error(`unexpected command ${command}`);
	}
}));
vi.mock('@tauri-apps/api/event', () => ({
	listen: async (_event: string, listener: (event: { payload: { percent: number | null } }) => void) => {
		shell.progressListener = listener;
		return () => {
			shell.progressListener = null;
			shell.unlistened += 1;
		};
	}
}));

const { CHECK_INTERVAL_MS, releasePage, UpdateStore } = await import('./update.svelte');

const VERSION = '0.3.0';

afterEach(() => {
	shell.check = async () => null;
	shell.install = async () => {};
	shell.unlistened = 0;
	vi.useRealTimers();
});

describe('UpdateStore', () => {
	test('offers an update the shell found', async () => {
		shell.check = async () => VERSION;
		const updates = new UpdateStore();
		await updates.check();
		expect(updates.state).toEqual({ status: 'available', version: VERSION });
	});

	test('keeps what it knew when a check fails', async () => {
		shell.check = async () => VERSION;
		const updates = new UpdateStore();
		await updates.check();
		shell.check = async () => {
			throw 'offline';
		};
		await updates.check();
		expect(updates.state).toEqual({ status: 'available', version: VERSION });
	});

	test('checks at once and again each day while watching', async () => {
		vi.useFakeTimers();
		let checks = 0;
		shell.check = async () => {
			checks += 1;
			return null;
		};
		const updates = new UpdateStore();
		updates.watch();
		expect(checks).toBe(1);
		await vi.advanceTimersByTimeAsync(CHECK_INTERVAL_MS);
		expect(checks).toBe(2);
		updates.unwatch();
		await vi.advanceTimersByTimeAsync(CHECK_INTERVAL_MS);
		expect(checks).toBe(2);
	});

	test('follows the download while installing', async () => {
		shell.check = async () => VERSION;
		const seen: unknown[] = [];
		const updates = new UpdateStore();
		await updates.check();
		shell.install = async (progress) => {
			progress(40);
			seen.push(updates.state);
			throw 'stopped here';
		};
		await updates.install();
		expect(seen).toEqual([{ status: 'installing', version: VERSION, percent: 40 }]);
		expect(shell.unlistened).toBe(1);
	});

	test('reports a failed install with the reason, and offers no second try until the next check', async () => {
		shell.check = async () => VERSION;
		let installs = 0;
		shell.install = async () => {
			installs += 1;
			throw 'pkexec was dismissed';
		};
		const updates = new UpdateStore();
		await updates.check();
		await updates.install();
		expect(updates.state).toEqual({ status: 'failed', version: VERSION, error: 'pkexec was dismissed' });
		await updates.install();
		expect(installs).toBe(1);
	});

	test('leaves an install that began while a check was waiting alone', async () => {
		shell.check = async () => VERSION;
		const updates = new UpdateStore();
		await updates.check();
		let answer: (version: string | null) => void = () => {};
		shell.check = () => new Promise((resolve) => (answer = resolve));
		const checking = updates.check();
		shell.install = () => new Promise(() => {});
		void updates.install();
		await vi.waitFor(() => expect(updates.state.status).toBe('installing'));
		answer(VERSION);
		await checking;
		expect(updates.state.status).toBe('installing');
	});

	test('leaves an install under way alone when a check comes due', async () => {
		shell.check = async () => VERSION;
		const updates = new UpdateStore();
		await updates.check();
		let finish: () => void = () => {};
		shell.install = () => new Promise((resolve) => (finish = resolve));
		const installing = updates.install();
		await vi.waitFor(() => expect(updates.state.status).toBe('installing'));
		shell.check = async () => null;
		await updates.check();
		expect(updates.state.status).toBe('installing');
		finish();
		await installing;
	});
});

describe('releasePage', () => {
	test('is the release of the offered version', () => {
		expect(releasePage(VERSION)).toBe('https://github.com/schrodlm/rentczecher/releases/tag/v0.3.0');
	});
});
