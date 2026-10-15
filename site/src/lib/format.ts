import type { Language } from '$lib/i18n';

const LOCALES: Record<Language, string> = { cs: 'cs-CZ', en: 'en-GB' };

/** Formats an ISO calendar date (YYYY-MM-DD) as written in the given language. */
export function formatDate(isoDate: string, lang: Language): string {
	const formatter = new Intl.DateTimeFormat(LOCALES[lang], { dateStyle: 'long', timeZone: 'UTC' });
	return formatter.format(new Date(`${isoDate}T00:00:00Z`));
}
