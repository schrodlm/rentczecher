export type Catalog = Record<string, string | string[]>;

export const CATALOGS: Record<string, () => Promise<Catalog>> = {
	cs: () => import('./cs.json').then((module) => module.default as Catalog),
	// English is the msgid source language, its catalog is empty by definition.
	en: async () => ({})
};
