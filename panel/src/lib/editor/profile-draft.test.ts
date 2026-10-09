import { describe, expect, test } from 'vitest';
import type { NamedPlace, ProfileModel } from '$lib/api/client';
import { ProfileDraft } from './profile-draft.svelte';

const PRAHA: NamedPlace = { kind: 'obec', code: 554782, name: 'Praha', obec: null, okres: null };
const PRAHA_7: NamedPlace = { kind: 'mestska_cast', code: 500186, name: 'Praha 7', obec: 'Praha', okres: null };

const STORED: ProfileModel = {
	id: 'p1',
	name: 'Praha byty',
	paused_at: '2026-10-01T08:00:00+00:00',
	portals: ['sreality', 'remax'],
	criteria: {
		offer_type: 'rent',
		estate_type: 'flat',
		place: PRAHA,
		min_price: 15000,
		max_price: 30000,
		min_size_m2: 40,
		max_size_m2: null,
		min_land_m2: null,
		dispositions: ['2+kk', '2+1']
	},
	preferences: {
		price_per_m2_weight: 10,
		disposition_weight: 20,
		preferred_dispositions: ['2+kk'],
		size_weight: 20,
		preferred_size_m2: 70,
		place_weight: 10,
		preferred_places: [PRAHA_7],
		land_weight: 0,
		preferred_land_m2: null,
		price_weight: 40,
		preferred_price: 22000
	}
};

function filledBlank(): ProfileDraft {
	const draft = ProfileDraft.blank();
	draft.name = '  Praha byty  ';
	draft.setPlace(PRAHA);
	return draft;
}

describe('ProfileDraft.blank', () => {
	test('watches every portal and waits for a name and a place', () => {
		const draft = ProfileDraft.blank();
		expect(draft.portals).toEqual(['sreality', 'bezrealitky', 'remax']);
		expect(draft.missing).toEqual(['name', 'place']);
		expect(draft.canSave).toBe(false);
	});

	test('can be saved once named and placed', () => {
		expect(filledBlank().canSave).toBe(true);
	});

	test('needs at least one portal', () => {
		const draft = filledBlank();
		draft.portals = [];
		expect(draft.missing).toEqual(['portals']);
	});
});

describe('ProfileDraft.of', () => {
	test('reads a stored profile', () => {
		const draft = ProfileDraft.of(STORED);
		expect(draft.name).toBe('Praha byty');
		expect(draft.paused).toBe(true);
		expect(draft.portals).toEqual(['sreality', 'remax']);
		expect(draft.place).toEqual(PRAHA);
		expect(draft.search).toMatchObject({ min_price: 15000, max_price: 30000, dispositions: ['2+kk', '2+1'] });
		expect(draft.preferredValues.preferred_places).toEqual([PRAHA_7]);
	});

	test('reads the weights of the preferences the editor offers', () => {
		expect(ProfileDraft.of(STORED).weights).toEqual({ price: 40, size: 20, land: 0, layout: 20, place: 10 });
	});
});

describe('crossedRanges', () => {
	test('reports a minimum typed above its maximum', () => {
		const draft = filledBlank();
		draft.search = { ...draft.search, min_price: 30000, max_price: 20000, min_size_m2: 80, max_size_m2: 50 };
		expect(draft.crossedRanges).toEqual(['price', 'size']);
		expect(draft.canSave).toBe(false);
	});

	test('ignores the size of land, which is not saved', () => {
		const draft = filledBlank();
		draft.search = { ...draft.search, estate_type: 'land', min_size_m2: 80, max_size_m2: 50 };
		expect(draft.crossedRanges).toEqual([]);
	});
});

describe('setOfferType', () => {
	test('clears every price when switching between rent and sale', () => {
		const draft = ProfileDraft.of(STORED);
		draft.setOfferType('sale');
		expect(draft.search).toMatchObject({ offer_type: 'sale', min_price: null, max_price: null });
		expect(draft.preferredValues.preferred_price).toBeNull();
	});

	test('keeps the prices when the offer stays the same', () => {
		const draft = ProfileDraft.of(STORED);
		draft.setOfferType('rent');
		expect(draft.search.min_price).toBe(15000);
	});
});

describe('setPlace', () => {
	test('clears the preferred places, which lie inside the old search place', () => {
		const draft = ProfileDraft.of(STORED);
		draft.setPlace({ kind: 'obec', code: 582786, name: 'Brno', obec: null, okres: null });
		expect(draft.preferredValues.preferred_places).toEqual([]);
	});
});

describe('newProfileBody', () => {
	test('sends the trimmed name, the place by its kind and code, and the preferences', () => {
		const draft = filledBlank();
		draft.preferredValues = { ...draft.preferredValues, preferred_price: 22000 };
		draft.weights = { ...draft.weights, price: 100 };
		const body = draft.newProfileBody();
		expect(body.name).toBe('Praha byty');
		expect(body.criteria.place).toEqual({ kind: 'obec', code: 554782 });
		expect(body.preferences).toMatchObject({ price_weight: 100, preferred_price: 22000 });
	});

	test('saves only the bounds that fit the estate type', () => {
		const draft = filledBlank();
		draft.search = { ...draft.search, min_size_m2: 40, min_land_m2: 500, dispositions: ['2+kk'] };
		expect(draft.newProfileBody().criteria).toMatchObject({ min_size_m2: 40, min_land_m2: null });
		draft.search = { ...draft.search, estate_type: 'land' };
		expect(draft.newProfileBody().criteria).toMatchObject({
			min_size_m2: null,
			min_land_m2: 500,
			dispositions: []
		});
	});

	test('refuses a profile without a search place', () => {
		expect(() => ProfileDraft.blank().newProfileBody()).toThrow();
	});
});

describe('updateBody', () => {
	test('sends what an existing profile can change', () => {
		const body = ProfileDraft.of(STORED).updateBody();
		expect(body).toMatchObject({ name: 'Praha byty', paused: true, portals: ['sreality', 'remax'] });
		expect(body.preferences).toMatchObject({ price_per_m2_weight: 0, price_weight: 45, disposition_weight: 22 });
	});
});
