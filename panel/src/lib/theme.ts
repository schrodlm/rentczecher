import { isTauri } from '@tauri-apps/api/core';
import { getCurrentWindow } from '@tauri-apps/api/window';
import type { Theme } from '$lib/user-config';

/* Shows the app in a theme: the stylesheet reads it from the root element,
and the window's title bar follows where the OS lets an app choose. */
export function applyTheme(theme: Theme): void {
	if (theme === 'system') delete document.documentElement.dataset.theme;
	else document.documentElement.dataset.theme = theme;
	if (isTauri()) void getCurrentWindow().setTheme(theme === 'system' ? null : theme);
}
