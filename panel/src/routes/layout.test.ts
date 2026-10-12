import { afterEach, describe, expect, test, vi } from 'vitest';

const shell = vi.hoisted(() => ({ file: null as string | null }));

vi.mock('@tauri-apps/api/core', () => ({
	isTauri: () => true,
	invoke: async (command: string) => (command === 'read_user_config' ? shell.file : null)
}));
vi.mock('@tauri-apps/api/window', () => ({ getCurrentWindow: () => ({ setTheme: async () => {} }) }));

const { load } = await import('./+layout');

afterEach(() => {
	shell.file = null;
	delete document.documentElement.dataset.theme;
});

// The load function only reads the address, so a bare event stands in for
// the one SvelteKit passes.
async function loadAt(address: string) {
	const event = { url: new URL(address) } as Parameters<typeof load>[0];
	return (await load(event)) as Exclude<Awaited<ReturnType<typeof load>>, void>;
}

describe('the layout', () => {
	test('starts a first run on the system, with no choices in the address', async () => {
		const data = await loadAt('http://app/');
		expect(data.firstRun).toBe(true);
		expect(data.userConfig.theme).toBe('system');
	});

	test('starts a first run on the choices the address carries', async () => {
		const data = await loadAt('http://app/?language=en&theme=dark');
		expect(data.userConfig).toEqual({ theme: 'dark', language: 'en' });
		expect(data.translator.language).toBe('en');
		expect(document.documentElement.dataset.theme).toBe('dark');
		expect(document.documentElement.lang).toBe('en');
	});

	test('ignores choices in the address that it does not know', async () => {
		const data = await loadAt('http://app/?language=de&theme=sepia');
		expect(data.userConfig.theme).toBe('system');
		expect(['cs', 'en']).toContain(data.userConfig.language);
	});

	test('opens on the saved config, whatever the address carries', async () => {
		shell.file = '{"version": 1, "theme": "light", "language": "cs"}';
		const data = await loadAt('http://app/?language=en&theme=dark');
		expect(data.firstRun).toBe(false);
		expect(data.userConfig).toEqual({ theme: 'light', language: 'cs' });
	});
});
