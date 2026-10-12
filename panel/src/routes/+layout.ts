import { Translator } from '$lib/i18n/translator';
import { applyTheme } from '$lib/theme';
import { LANGUAGES, systemUserConfig, THEMES, UserConfigFile, type UserConfig } from '$lib/user-config';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async ({ url }) => {
	const stored = await new UserConfigFile().load();
	const userConfig = stored ?? firstRunConfig(url);
	// Before the first paint, so the app never flashes the other theme.
	applyTheme(userConfig.theme);
	const translator = await Translator.load(userConfig.language);
	// Screen readers and hyphenation read the page in this language.
	document.documentElement.lang = translator.language;
	return { translator, userConfig, firstRun: stored === null };
};

/* Before anyone chooses, the app follows the system, except for what the
welcome wizard was told so far, which it carries in the address across the
reload a language change makes. */
function firstRunConfig(url: URL): UserConfig {
	const system = systemUserConfig(navigator.languages);
	const told = url.searchParams;
	return {
		theme: THEMES.find((theme) => theme === told.get('theme')) ?? system.theme,
		language: LANGUAGES.find((language) => language === told.get('language')) ?? system.language
	};
}
