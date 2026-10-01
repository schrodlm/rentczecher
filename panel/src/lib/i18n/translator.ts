import { CATALOGS, type Catalog } from './catalog';
import { PLURAL_SELECTORS, type PluralSelector } from './plural-rules';

// The msgid convention: English is the source language, written literally at
// every call site. Its catalog is empty by definition, and a missing entry
// in any other language falls back to rendering the English msgid itself.
const SOURCE_LANGUAGE = 'en';

// Fills a message's {name} placeholders from the params the call site
// passes at runtime: "{count} profiles" with {count: 5} becomes
// "5 profiles". A placeholder with no matching param stays as is,
// visibly unfilled in the UI.
function interpolate(template: string, params: Record<string, string | number>): string {
	return template.replace(/\{(\w+)\}/g, (placeholder, name) =>
		name in params ? String(params[name]) : placeholder
	);
}

/* Loads one language's catalog and renders its messages, honoring that
language's own plural-form count rather than assuming two forms. Czech
carries three (one, few, many). */
export class Translator {
	private constructor(
		private readonly catalog: Catalog,
		private readonly selectPlural: PluralSelector
	) {}

	static async load(language: string): Promise<Translator> {
		const loadCatalog = CATALOGS[language];
		if (!loadCatalog) {
			throw new Error(`no catalog registered for language "${language}"`);
		}
		const selectPlural = PLURAL_SELECTORS[language];
		if (!selectPlural) {
			throw new Error(`no plural selector registered for language "${language}"`);
		}
		const catalog = await loadCatalog();
		return new Translator(catalog, selectPlural);
	}

	t(msgid: string, params: Record<string, string | number> = {}): string {
		const message = this.catalog[msgid];
		if (message === undefined) {
			return interpolate(msgid, params);
		}
		if (Array.isArray(message)) {
			throw new Error(`"${msgid}" is a plural message, call tn() instead of t()`);
		}
		return interpolate(message, params);
	}

	tn(
		msgid: string,
		msgidPlural: string,
		count: number,
		params: Record<string, string | number> = {}
	): string {
		const message = this.catalog[msgid];
		if (message === undefined) {
			const sourceForm = PLURAL_SELECTORS[SOURCE_LANGUAGE](count) === 0 ? msgid : msgidPlural;
			return interpolate(sourceForm, { count, ...params });
		}
		if (!Array.isArray(message)) {
			throw new Error(`"${msgid}" is a plain message, call t() instead of tn()`);
		}
		const formIndex = this.selectPlural(count);
		const form = message[formIndex];
		if (form === undefined) {
			throw new Error(`"${msgid}" has no plural form at index ${formIndex}`);
		}
		return interpolate(form, { count, ...params });
	}
}
