import type { Language } from '$lib/user-config';
import { CATALOGS, type Catalog } from './catalog';
import { PLURAL_SELECTORS, type PluralSelector } from './plural-rules';

// The msgid convention: English is the source language, written literally at
// every call site. Its catalog is empty by definition, and a missing entry
// in any other language falls back to rendering the English msgid itself.
const SOURCE_LANGUAGE = 'en';

// The conventions each language writes numbers and dates by. English takes
// the British ones, day before month.
const LOCALES: Record<Language, string> = { cs: 'cs-CZ', en: 'en-GB' };

// Keeps a number and its unit together on one line.
const NBSP = '\u00a0';

// Fills a message's {name} placeholders from the params the call site
// passes at runtime: "{count} profiles" with {count: 5} becomes
// "5 profiles". A placeholder with no matching param stays as is,
// visibly unfilled in the UI.
function interpolate(template: string, params: Record<string, string | number>): string {
	return template.replace(/\{(\w+)\}/g, (placeholder, name) =>
		name in params ? String(params[name]) : placeholder
	);
}

/* Speaks one language: renders its messages, honoring its own plural-form
count rather than assuming two forms, as Czech carries three (one, few,
many), and writes numbers and dates the way it does. */
export class Translator {
	private readonly locale: string;

	private constructor(
		readonly language: Language,
		private readonly catalog: Catalog,
		private readonly selectPlural: PluralSelector
	) {
		this.locale = LOCALES[language];
	}

	static async load(language: Language): Promise<Translator> {
		const loadCatalog = CATALOGS[language];
		if (!loadCatalog) {
			throw new Error(`no catalog registered for language "${language}"`);
		}
		const selectPlural = PLURAL_SELECTORS[language];
		if (!selectPlural) {
			throw new Error(`no plural selector registered for language "${language}"`);
		}
		const catalog = await loadCatalog();
		return new Translator(language, catalog, selectPlural);
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

	/* A number with its thousands grouped the language's way, never broken
	across lines. */
	number(value: number): string {
		return value.toLocaleString(this.locale).replace(/\s/g, NBSP);
	}

	price(price: number): string {
		return `${this.number(price)}${NBSP}Kč`;
	}

	pricePerM2(price: number, sizeM2: number): string | null {
		if (sizeM2 <= 0) return null;
		return this.perM2(price / sizeM2);
	}

	perM2(pricePerM2: number): string {
		return `${this.price(Math.round(pricePerM2))}/m²`;
	}

	area(m2: number): string {
		return `${this.number(m2)}${NBSP}m²`;
	}

	/* A number as a slider's box shows it, and an empty box for no number.
	parseTypedNumber reads it back. */
	typedNumber(value: number | null): string {
		return value === null ? '' : value.toLocaleString(this.locale);
	}

	dayAndMonth(iso: string): string {
		return new Date(iso).toLocaleDateString(this.locale, { day: 'numeric', month: 'numeric' });
	}

	date(iso: string): string {
		return new Date(iso).toLocaleDateString(this.locale, { day: 'numeric', month: 'numeric', year: 'numeric' });
	}

	time(moment: Date): string {
		return moment.toLocaleTimeString(this.locale);
	}
}
