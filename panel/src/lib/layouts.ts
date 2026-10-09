import type { components } from '$lib/api/types.gen';
import type { Translator } from '$lib/i18n/translator';

export type Layout = components['schemas']['CriteriaBody']['dispositions'][number];

/* Every layout the engine knows, by room count, a kitchenette before a
separate kitchen, and the atypical ones last. */
export const LAYOUTS: readonly Layout[] = [
	'1+kk', '1+1', '2+kk', '2+1', '3+kk', '3+1', '4+kk', '4+1', '5+kk', '5+1',
	'6+kk', '6+1', '7+kk', '7+1', '8+kk', '8+1', '9+kk', '9+1', 'atypicky'
];

/* The layouts side by side for each room count, the atypical ones alone. */
export function layoutsByRooms(): Layout[][] {
	const groups: Layout[][] = [];
	for (const layout of LAYOUTS) {
		const last = groups.at(-1);
		if (last && layout !== 'atypicky' && rooms(last[0]) === rooms(layout)) last.push(layout);
		else groups.push([layout]);
	}
	return groups;
}

function rooms(layout: Layout): string {
	return layout.split('+')[0];
}

/* A layout as the user reads it. Only the atypical one is a word. */
export function layoutName(layout: Layout, t: Translator): string {
	return layout === 'atypicky' ? t.t('atypical') : layout;
}
