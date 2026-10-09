import { describe, expect, test } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import type { components } from '$lib/api/types.gen';
import {
	countingFor,
	isReady,
	preferencesBody,
	storedWeights,
	PREFERENCES,
	preferencesFor,
	type Weights,
	type Preference,
	type PreferredValues
} from './preferences';

type PreferencesBody = components['schemas']['PreferencesBody'];

const HOLESOVICE: NamedPlace = { kind: 'cast_obce', code: 490067, name: 'Holešovice', obec: 'Praha', okres: null };

const NO_VALUES: PreferredValues = {
	preferred_price: null,
	preferred_size_m2: null,
	preferred_land_m2: null,
	preferred_dispositions: [],
	preferred_places: []
};

const VALUES: PreferredValues = {
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

describe('preferencesFor', () => {
	test.each([
		['flat', ['price', 'size', 'layout', 'place']],
		['house', ['price', 'size', 'land', 'layout', 'place']],
		['cottage', ['price', 'size', 'land', 'layout', 'place']],
		['land', ['price', 'land', 'place']]
	] as const)('offers a %s the preferences that fit it', (estateType, preferences) => {
		expect(preferencesFor(estateType)).toEqual(preferences);
	});
});

describe('isReady', () => {
	test('holds no preference ready without its preferred value', () => {
		expect(PREFERENCES.filter((preference) => isReady(preference, NO_VALUES))).toEqual([]);
	});

	const values: [Preference, Partial<PreferredValues>][] = [
		['price', { preferred_price: 22000 }],
		['size', { preferred_size_m2: 70 }],
		['land', { preferred_land_m2: 800 }],
		['layout', { preferred_dispositions: ['2+kk'] }],
		['place', { preferred_places: [HOLESOVICE] }]
	];
	test.each(values)('holds %s ready once it has its preferred value', (preference, value) => {
		expect(isReady(preference, { ...NO_VALUES, ...value })).toBe(true);
	});
});

describe('countingFor', () => {
	test('counts the preferences that fit the estate and have their preferred value', () => {
		const set = { ...VALUES, preferred_size_m2: null };
		expect(countingFor(set, 'flat')).toEqual(['price', 'layout', 'place']);
	});
});

describe('storedWeights', () => {
	test('grows the counting preferences to fill the share of one whose preferred value was cleared', () => {
		const set = { ...VALUES, preferred_price: null, preferred_places: [] };
		expect(storedWeights(set, weights({ price: 50, size: 30, layout: 20 }), 'flat')).toEqual(
			weights({ size: 60, layout: 40 })
		);
	});

	test('stores no weight for a preference that does not fit the estate', () => {
		const set = { ...NO_VALUES, preferred_price: 22000, preferred_land_m2: 800 };
		expect(storedWeights(set, weights({ price: 50, land: 50 }), 'flat')).toEqual(weights({ price: 100 }));
	});
});

describe('preferencesBody', () => {
	test('keeps every preferred value, a place by its kind and code, and the stored weights', () => {
		const set = weights({ price: 30, size: 20, land: 20, layout: 15, place: 15 });
		expect(preferencesBody(VALUES, set, 'house')).toEqual({
			...UNSET,
			preferred_price: 22000,
			preferred_size_m2: 70,
			preferred_land_m2: 800,
			preferred_dispositions: ['2+kk'],
			preferred_places: [{ kind: 'cast_obce', code: 490067 }],
			price_weight: 30,
			size_weight: 20,
			land_weight: 20,
			disposition_weight: 15,
			place_weight: 15
		});
	});

	test('weighs nothing while no preferred value is set', () => {
		const preferences = preferencesBody(NO_VALUES, weights({}), 'flat');
		expect([preferences.price_weight, preferences.size_weight, preferences.place_weight]).toEqual([0, 0, 0]);
	});
});
