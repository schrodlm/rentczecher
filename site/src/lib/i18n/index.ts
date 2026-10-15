import { cs } from './cs';
import { en } from './en';
import type { Messages } from './messages';

export type Language = 'cs' | 'en';

export const DEFAULT_LANGUAGE: Language = 'cs';

// Every language but the default is served under its own path prefix.
export const ALTERNATE_LANGUAGES: Language[] = ['en'];

export const LANGUAGES: Language[] = [DEFAULT_LANGUAGE, ...ALTERNATE_LANGUAGES];

export const MESSAGES: Record<Language, Messages> = { cs, en };

export function isAlternateLanguage(param: string): param is Language {
	return ALTERNATE_LANGUAGES.some((lang) => lang === param);
}

export function homePath(lang: Language): string {
	return lang === DEFAULT_LANGUAGE ? '/' : `/${lang}/`;
}
