/*
Selects the plural form index for a count, per language, mirroring each
catalog's own Plural-Forms header. A gettext header carries a C expression;
rather than evaluating that expression at runtime, every supported language
gets its selector spelled out here once, so the formula a translator reads
in the .po file and the formula the app runs stay obviously the same thing.
*/

export type PluralSelector = (count: number) => number;

export const PLURAL_SELECTORS: Record<string, PluralSelector> = {
	// nplurals=3; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2;
	cs: (n) => (n === 1 ? 0 : n >= 2 && n <= 4 ? 1 : 2),
	// nplurals=2; plural=(n!=1);
	en: (n) => (n !== 1 ? 1 : 0)
};
