import { describe, expect, test } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import type { components } from '$lib/api/types.gen';
import {
	countingFor,
	isReady,
	preferencesFor,
	storedWeights,
	WISHES,
	wishesFor,
	type Weights,
	type Wish,
	type WishSettings
} from './wishes';

type PreferencesBody = components['schemas']['PreferencesBody'];

const HOLESOVICE: NamedPlace = { kind: 'cast_obce', code: 490067, name: 'Holešovice', obec: 'Praha', okres: null };

const NO_SETTINGS: WishSettings = {
	preferred_price: null,
	preferred_size_m2: null,
	preferred_land_m2: null,
	preferred_dispositions: [],
	preferred_places: []
};

const SETTINGS: WishSettings = {
	preferred_price: 22000,
	preferred_size_m2: 70,
	preferred_land_m2: 800,
	preferred_dispositions: ['2+kk'],
	preferred_places: [HOLESOVICE]
};

const UNSET: PreferencesBody = {
	price_per_m2_weight: 0,
	disposition_weight: 0,
	preferred_dispositions: [],
	size_weight: 0,
	preferred_size_m2: null,
	place_weight: 0,
	preferred_places: [],
	land_weight: 0,
	preferred_land_m2: null,
	price_weight: 0,
	preferred_price: null
};

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
		expect(WISHES.filter((wish) => isReady(wish, NO_SETTINGS))).toEqual([]);
	});

	const settings: [Wish, Partial<WishSettings>][] = [
		['price', { preferred_price: 22000 }],
		['size', { preferred_size_m2: 70 }],
		['land', { preferred_land_m2: 800 }],
		['layout', { preferred_dispositions: ['2+kk'] }],
		['place', { preferred_places: [HOLESOVICE] }]
	];
	test.each(settings)('holds %s ready once it has its setting', (wish, setting) => {
		expect(isReady(wish, { ...NO_SETTINGS, ...setting })).toBe(true);
	});
});

describe('countingFor', () => {
	test('counts the wishes that fit the estate, have their setting and are on', () => {
		const set = { ...SETTINGS, preferred_size_m2: null };
		const on = weights({ price: 40, size: 20, land: 20, layout: 20 });
		expect(countingFor(set, on, 'flat')).toEqual(['price', 'layout']);
	});
});

describe('storedWeights', () => {
	test('grows the counting wishes to fill the share of one whose setting was cleared', () => {
		const set = { ...SETTINGS, preferred_price: null };
		expect(storedWeights(set, weights({ price: 50, size: 30, layout: 20 }), 'flat')).toEqual(
			weights({ size: 60, layout: 40 })
		);
	});

	test('stores no weight for a wish that does not fit the estate', () => {
		expect(storedWeights(SETTINGS, weights({ price: 50, land: 50 }), 'flat')).toEqual(weights({ price: 100 }));
	});
});

describe('preferencesFor', () => {
	test('keeps every setting, a place by its kind and code, and the stored weights', () => {
		expect(preferencesFor(SETTINGS, weights({ price: 60, size: 40 }), 'house')).toEqual({
			...UNSET,
			preferred_price: 22000,
			preferred_size_m2: 70,
			preferred_land_m2: 800,
			preferred_dispositions: ['2+kk'],
			preferred_places: [{ kind: 'cast_obce', code: 490067 }],
			price_weight: 60,
			size_weight: 40
		});
	});

	test('weighs nothing while no wish is on', () => {
		const preferences = preferencesFor(SETTINGS, weights({}), 'flat');
		expect([preferences.price_weight, preferences.size_weight, preferences.place_weight]).toEqual([0, 0, 0]);
	});
});
