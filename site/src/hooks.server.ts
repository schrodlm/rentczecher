import type { Handle } from '@sveltejs/kit';
import { DEFAULT_LANGUAGE, isAlternateLanguage } from '$lib/i18n';

export const handle: Handle = async ({ event, resolve }) => {
	const param = event.params.lang;
	const lang = param !== undefined && isAlternateLanguage(param) ? param : DEFAULT_LANGUAGE;
	return resolve(event, {
		transformPageChunk: ({ html }) => html.replace('%lang%', lang)
	});
};
