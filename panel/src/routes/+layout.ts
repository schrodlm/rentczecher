import { Translator } from '$lib/i18n/translator';
import { applyTheme } from '$lib/theme';
import { systemLanguage, UserConfigFile } from '$lib/user-config';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async () => {
	const userConfig = await new UserConfigFile().load();
	// Before the first paint, so the app never flashes the other theme.
	applyTheme(userConfig?.theme ?? 'system');
	const translator = await Translator.load(userConfig?.language ?? systemLanguage(navigator.languages));
	// Screen readers and hyphenation read the page in this language.
	document.documentElement.lang = translator.language;
	return { translator };
};
