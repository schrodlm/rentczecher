import { afterEach, describe, expect, test, vi } from 'vitest';

const shell = vi.hoisted(() => ({ inApp: false, windowThemes: [] as (string | null)[] }));

vi.mock('@tauri-apps/api/core', () => ({ isTauri: () => shell.inApp }));
vi.mock('@tauri-apps/api/window', () => ({
	getCurrentWindow: () => ({
		setTheme: async (theme: string | null) => {
			shell.windowThemes.push(theme);
		}
	})
}));

const { applyTheme } = await import('./theme');

afterEach(() => {
	shell.inApp = false;
	shell.windowThemes = [];
	delete document.documentElement.dataset.theme;
});

describe('applyTheme', () => {
	test('marks the root element with a chosen theme', () => {
		applyTheme('dark');
		expect(document.documentElement.dataset.theme).toBe('dark');
		applyTheme('light');
		expect(document.documentElement.dataset.theme).toBe('light');
	});

	test('leaves the root element unmarked to follow the system', () => {
		applyTheme('dark');
		applyTheme('system');
		expect(document.documentElement.dataset.theme).toBeUndefined();
	});

	test('sets the window to the theme in the app, and back to the system for system', () => {
		shell.inApp = true;
		applyTheme('dark');
		applyTheme('system');
		expect(shell.windowThemes).toEqual(['dark', null]);
	});

	test('leaves the window alone outside the app', () => {
		applyTheme('dark');
		expect(shell.windowThemes).toEqual([]);
	});
});
