import { describe, expect, test } from 'vitest';
import type { components } from '$lib/api/types.gen';
import { importancesFrom, isReady, weightsFor, WISHES, wishesFor, type Importances, type Weights, type Wish } from './wishes';

type PreferencesBody = components['schemas']['PreferencesBody'];

const UNSET: PreferencesBody = {
	price_per_m2_weight: 0,
	disposition_weight: 0,
	preferred_dispositions: [],
	size_weight: 0,
	ideal_size_m2: null,
	place_weight: 0,
	preferred_places: [],
	land_weight: 0,
	ideal_land_m2: null,
	price_weight: 0,
	max_good_price: null
};

function importances(set: Partial<Importances>): Importances {
	return { price: 0, size: 0, land: 0, layout: 0, place: 0, ...set };
}

function weights(set: Partial<Weights>): Weights {
	return { price: 0, size: 0, land: 0, layout: 0, place: 0, ...set };
}

describe('wishesFor', () => {
	test.each([
		['flat', ['price', 'size', 'layout', 'place']],
		['house', ['price', 'size', 'land', 'layout', 'place']],
		['cottage', ['price', 'size', 'land', 'layout', 'place']],
		['land', ['price', 'land', 'place']]
	] as const)('offers a %s the wishes that fit it', (estateType, wishes) => {
		expect(wishesFor(estateType)).toEqual(wishes);
	});
});

describe('isReady', () => {
	test('holds no wish ready without its setting', () => {
		expect(WISHES.filter((wish) => isReady(wish, UNSET))).toEqual([]);
	});

	const settings: [Wish, Partial<PreferencesBody>][] = [
		['price', { max_good_price: 22000 }],
		['size', { ideal_size_m2: 70 }],
		['land', { ideal_land_m2: 800 }],
		['layout', { preferred_dispositions: ['2+kk'] }],
		['place', { preferred_places: [{ kind: 'cast_obce', code: 490067 }] }]
	];
	test.each(settings)('holds %s ready once it has its setting', (wish, setting) => {
		expect(isReady(wish, { ...UNSET, ...setting })).toBe(true);
	});
});

describe('weightsFor', () => {
	test('splits 100 by importance, top counting five times low', () => {
		expect(weightsFor(importances({ price: 4, size: 1 }), ['price', 'size'])).toEqual(
			weights({ price: 83, size: 17 })
		);
	});

	test('always adds up to exactly 100', () => {
		const result = weightsFor(importances({ price: 1, size: 1, layout: 1 }), ['price', 'size', 'layout']);
		expect(result).toEqual(weights({ price: 34, size: 33, layout: 33 }));
	});

	test('gives no weight to a wish that does not count', () => {
		const result = weightsFor(importances({ price: 4, land: 4 }), ['price']);
		expect(result).toEqual(weights({ price: 100 }));
	});

	test('gives nothing any weight when no wish matters', () => {
		expect(weightsFor(importances({}), [...WISHES])).toEqual(weights({}));
	});
});

describe('importancesFrom', () => {
	test('reads back the importances an editor saved', () => {
		const saved = importances({ price: 4, size: 1, layout: 3, place: 2 });
		const counting = ['price', 'size', 'layout', 'place'] as const;
		expect(importancesFrom(weightsFor(saved, counting))).toEqual(saved);
	});

	test('reads equal weights back as the highest importances that fit', () => {
		expect(importancesFrom(weights({ price: 50, size: 50 }))).toEqual(importances({ price: 4, size: 4 }));
	});

	test('reproduces the weights of every importance the editor can save', () => {
		for (const price of [0, 1, 2, 3, 4] as const) {
			for (const size of [0, 1, 2, 3, 4] as const) {
				for (const layout of [0, 1, 2, 3, 4] as const) {
					const saved = weightsFor(importances({ price, size, layout }), WISHES);
					expect(weightsFor(importancesFrom(saved), WISHES)).toEqual(saved);
				}
			}
		}
	});

	test('reads the nearest importances for weights the editor did not save', () => {
		expect(importancesFrom(weights({ price: 60, size: 40 }))).toEqual(importances({ price: 3, size: 2 }));
	});
});
