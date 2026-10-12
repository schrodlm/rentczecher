import { afterEach, describe, expect, test, vi } from 'vitest';

const shell = vi.hoisted(() => ({
	inApp: false,
	file: null as string | null,
	unreadable: false,
	writes: [] as string[]
}));

vi.mock('@tauri-apps/api/core', () => ({
	isTauri: () => shell.inApp,
	invoke: async (command: string, args: { contents: string }) => {
		if (command === 'write_user_config') {
			shell.writes.push(args.contents);
			return null;
		}
		if (command !== 'read_user_config') throw new Error(`unexpected command ${command}`);
		if (shell.unreadable) throw new Error('could not read user_config.json: permission denied');
		return shell.file;
	}
}));

const { parseUserConfig, serializeUserConfig, systemLanguage, systemUserConfig, UserConfigFile } = await import(
	'./user-config'
);

afterEach(() => {
	shell.inApp = false;
	shell.file = null;
	shell.unreadable = false;
	shell.writes = [];
});

describe('systemLanguage', () => {
	test('reads Czech from a Czech or Slovak system', () => {
		expect(systemLanguage(['cs-CZ', 'en-US'])).toBe('cs');
		expect(systemLanguage(['cs'])).toBe('cs');
		expect(systemLanguage(['sk-SK'])).toBe('cs');
		expect(systemLanguage(['CS-cz'])).toBe('cs');
	});

	test('reads English from any other system, or one naming no language', () => {
		expect(systemLanguage(['en-GB', 'cs-CZ'])).toBe('en');
		expect(systemLanguage(['de-DE'])).toBe('en');
		expect(systemLanguage([])).toBe('en');
	});
});

describe('parseUserConfig', () => {
	test('reads the config this panel writes', () => {
		expect(parseUserConfig('{"version": 1, "theme": "dark", "language": "en"}')).toEqual({
			theme: 'dark',
			language: 'en'
		});
	});

	test('reads nothing from text that is not exactly such a config', () => {
		expect(parseUserConfig('{"version": 1, "theme": "dark"')).toBeNull();
		expect(parseUserConfig('null')).toBeNull();
		expect(parseUserConfig('"dark"')).toBeNull();
		expect(parseUserConfig('{"version": 2, "theme": "dark", "language": "en"}')).toBeNull();
		expect(parseUserConfig('{"theme": "dark", "language": "en"}')).toBeNull();
		expect(parseUserConfig('{"version": 1, "theme": "sepia", "language": "en"}')).toBeNull();
		expect(parseUserConfig('{"version": 1, "theme": "dark", "language": "de"}')).toBeNull();
	});
});

describe('serializeUserConfig', () => {
	test('writes a config the panel reads back as it was', () => {
		const config = { theme: 'dark', language: 'en' } as const;
		expect(parseUserConfig(serializeUserConfig(config))).toEqual(config);
	});
});

describe('UserConfigFile', () => {
	test('saves a config through the shell', async () => {
		shell.inApp = true;
		await new UserConfigFile().save({ theme: 'light', language: 'cs' });
		expect(shell.writes.map(parseUserConfig)).toEqual([{ theme: 'light', language: 'cs' }]);
	});

	test('keeps nothing outside the app', async () => {
		await new UserConfigFile().save({ theme: 'light', language: 'cs' });
		expect(shell.writes).toEqual([]);
	});

	test('loads the config the shell keeps', async () => {
		shell.inApp = true;
		shell.file = '{"version": 1, "theme": "light", "language": "cs"}';
		expect(await new UserConfigFile().load()).toEqual({ theme: 'light', language: 'cs' });
	});

	test('loads nothing on the first run, when the shell keeps no file', async () => {
		shell.inApp = true;
		expect(await new UserConfigFile().load()).toBeNull();
	});

	test('loads nothing from a file that is not a config or cannot be read', async () => {
		shell.inApp = true;
		shell.file = 'theme = dark';
		expect(await new UserConfigFile().load()).toBeNull();
		shell.file = null;
		shell.unreadable = true;
		expect(await new UserConfigFile().load()).toBeNull();
	});

	test('loads the system config outside the app, without asking the shell', async () => {
		shell.file = '{"version": 1, "theme": "dark", "language": "en"}';
		expect(await new UserConfigFile().load()).toEqual(systemUserConfig(navigator.languages));
	});
});
