import { invoke, isTauri } from '@tauri-apps/api/core';

export type Theme = 'system' | 'light' | 'dark';
export type Language = 'cs' | 'en';

/* What a person chose about the app itself on this machine. */
export type UserConfig = { theme: Theme; language: Language };

export const THEMES: readonly Theme[] = ['system', 'light', 'dark'];
export const LANGUAGES: readonly Language[] = ['cs', 'en'];

// The format this panel writes. A file of any other version reads as no
// config at all, so it is never misread.
const VERSION = 1;

/* The language a person most likely reads, from the system's own list:
Czech for a Czech or Slovak system, English otherwise. */
export function systemLanguage(systemLanguages: readonly string[]): Language {
	const first = systemLanguages[0]?.toLowerCase() ?? '';
	return first.startsWith('cs') || first.startsWith('sk') ? 'cs' : 'en';
}

/* The config as the system would have it, before anyone chose. */
export function systemUserConfig(systemLanguages: readonly string[]): UserConfig {
	return { theme: 'system', language: systemLanguage(systemLanguages) };
}

/* Null when the text is not a config this panel writes. */
export function parseUserConfig(text: string): UserConfig | null {
	let parsed: unknown;
	try {
		parsed = JSON.parse(text);
	} catch {
		return null;
	}
	if (typeof parsed !== 'object' || parsed === null) return null;
	const { version, theme, language } = parsed as Record<string, unknown>;
	if (version !== VERSION) return null;
	const knownTheme = THEMES.find((each) => each === theme);
	const knownLanguage = LANGUAGES.find((each) => each === language);
	if (knownTheme === undefined || knownLanguage === undefined) return null;
	return { theme: knownTheme, language: knownLanguage };
}

/* The config file the shell keeps. Outside the app, as in a browser tab
during development, there is no file: the config is the system's and is
never asked for. */
export class UserConfigFile {
	/* Null on the first run, while no readable config exists. A file that
	cannot be read or is not a config is left as it is until a new config
	replaces it. */
	async load(): Promise<UserConfig | null> {
		if (!isTauri()) return systemUserConfig(navigator.languages);
		let text: string | null;
		try {
			text = await invoke<string | null>('read_user_config');
		} catch {
			return null;
		}
		return text === null ? null : parseUserConfig(text);
	}
}
