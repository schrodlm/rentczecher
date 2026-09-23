import { Translator } from '$lib/i18n/translator';
import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async () => {
	const translator = await Translator.load('cs');
	return { translator };
};
