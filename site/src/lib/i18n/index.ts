import { cs } from './cs';
import { en } from './en';
import type { Messages } from './messages';

export type Language = 'cs' | 'en';

export const DEFAULT_LANGUAGE: Language = 'cs';

// Every language but the default is served under its own path prefix.
export const ALTERNATE_LANGUAGES: Language[] = ['en'];

// Devlog posts are written in one language only, whichever page links to them.
export const DEVLOG_LANGUAGE: Language = 'en';

export const LANGUAGES: Language[] = [DEFAULT_LANGUAGE, ...ALTERNATE_LANGUAGES];

export const MESSAGES: Record<Language, Messages> = { cs, en };

export function isAlternateLanguage(param: string): param is Language {
	return ALTERNATE_LANGUAGES.some((lang) => lang === param);
}

export function homePath(lang: Language): string {
	return lang === DEFAULT_LANGUAGE ? '/' : `/${lang}/`;
}

/** The same page in every language, for a page that exists in all of them. */
export function pathsInEveryLanguage(pageWithinLanguage: string): Record<Language, string> {
	return { cs: `${homePath('cs')}${pageWithinLanguage}`, en: `${homePath('en')}${pageWithinLanguage}` };
}
