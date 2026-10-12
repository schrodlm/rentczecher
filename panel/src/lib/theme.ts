import { isTauri } from '@tauri-apps/api/core';
import { getCurrentWindow } from '@tauri-apps/api/window';
import type { Translator } from '$lib/i18n/translator';
import type { Theme } from '$lib/user-config';

export function themeName(theme: Theme, t: Translator): string {
	if (theme === 'light') return t.t('Light');
	if (theme === 'dark') return t.t('Dark');
	return t.t('Follow the system');
}

/* Shows the app in a theme: the stylesheet reads it from the root element,
and the window's title bar follows where the OS lets an app choose. */
export function applyTheme(theme: Theme): void {
	if (theme === 'system') delete document.documentElement.dataset.theme;
	else document.documentElement.dataset.theme = theme;
	if (isTauri()) void getCurrentWindow().setTheme(theme === 'system' ? null : theme);
}
