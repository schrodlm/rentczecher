import { Translator } from '$lib/i18n/translator';
import { systemLanguage, UserConfigFile } from '$lib/user-config';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async () => {
	const userConfig = await new UserConfigFile().load();
	const translator = await Translator.load(userConfig?.language ?? systemLanguage(navigator.languages));
	return { translator };
};
