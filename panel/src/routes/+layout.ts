import { Translator } from '$lib/i18n/translator';
import { applyTheme } from '$lib/theme';
import { systemUserConfig, UserConfigFile } from '$lib/user-config';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async () => {
	// Before anyone chooses, the app follows the system.
	const userConfig = (await new UserConfigFile().load()) ?? systemUserConfig(navigator.languages);
	// Before the first paint, so the app never flashes the other theme.
	applyTheme(userConfig.theme);
	const translator = await Translator.load(userConfig.language);
	// Screen readers and hyphenation read the page in this language.
	document.documentElement.lang = translator.language;
	return { translator, userConfig };
};
