import type { Handle, RequestEvent } from '@sveltejs/kit';
import { DEFAULT_LANGUAGE, DEVLOG_LANGUAGE, isAlternateLanguage, type Language } from '$lib/i18n';

function languageOf(event: RequestEvent): Language {
	if (event.route.id?.startsWith('/devlog')) return DEVLOG_LANGUAGE;
	const param = event.params.lang;
	return param !== undefined && isAlternateLanguage(param) ? param : DEFAULT_LANGUAGE;
}

export const handle: Handle = async ({ event, resolve }) => {
	const lang = languageOf(event);
	return resolve(event, {
		transformPageChunk: ({ html }) => html.replace('%lang%', lang)
	});
};
