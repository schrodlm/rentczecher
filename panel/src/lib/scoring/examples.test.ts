import { describe, expect, test } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { exampleListings, type ExampleProfile } from './examples';

const PRAHA: NamedPlace = { kind: 'obec', code: 554782, name: 'Praha', obec: null, okres: null };
const PRAHA_7: NamedPlace = { kind: 'mestska_cast', code: 500186, name: 'Praha 7', obec: 'Praha', okres: null };
const PRAHA_8: NamedPlace = { kind: 'mestska_cast', code: 500208, name: 'Praha 8', obec: 'Praha', okres: null };

const FLAT_TO_RENT: ExampleProfile = {
	criteria: {
		estate_type: 'flat',
		offer_type: 'rent',
		min_price: null,
		max_price: null,
		min_size_m2: null,
		max_size_m2: null,
		min_land_m2: null,
		dispositions: []
	},
	searchPlace: PRAHA,
	preferredValues: {
		preferred_price: 22000,
		preferred_size_m2: 70,
		preferred_land_m2: null,
		preferred_dispositions: ['2+kk', '2+1'],
		preferred_places: [PRAHA_7, PRAHA_8]
	},
	weights: { price: 25, size: 25, land: 0, layout: 25, place: 25 }
};

function profile(criteria: Partial<ExampleProfile['criteria']>): ExampleProfile {
	return { ...FLAT_TO_RENT, criteria: { ...FLAT_TO_RENT.criteria, ...criteria } };
}

describe('exampleListings', () => {
	test('picks the listing scoring nearest each of 100, 50 and 10', () => {
		const cards = exampleListings(FLAT_TO_RENT);
		expect(cards.map((card) => [card.target, card.score])).toEqual([
			[100, 100],
			[50, 67],
			[10, 10]
		]);
	});

	test('marks a target the listings jump past', () => {
		const cards = exampleListings(FLAT_TO_RENT);
		expect(cards.map((card) => card.nearTarget)).toEqual([true, false, true]);
	});

	test('puts the best listing on both preferred lists', () => {
		const [best] = exampleListings(FLAT_TO_RENT);
		expect(best).toMatchObject({
			score: 100,
			layout: '2+kk',
			layoutPreferred: true,
			place: PRAHA_7,
			placePreferred: true
		});
		expect(best.price).toBeLessThanOrEqual(22000);
	});

	test('keeps the worst listing off the preferred lists', () => {
		const worst = exampleListings(FLAT_TO_RENT).at(-1)!;
		expect(worst).toMatchObject({ layoutPreferred: false, placePreferred: false, place: PRAHA });
		expect(['2+kk', '2+1']).not.toContain(worst.layout);
	});

	test('breaks every score into the parts it adds up from', () => {
		for (const card of exampleListings(FLAT_TO_RENT)) {
			const total = card.parts.reduce((sum, part) => sum + part.points, 0);
			expect(Math.abs(total - card.score)).toBeLessThanOrEqual(0.5);
		}
	});

	test('stays within the search limits', () => {
		const limited = profile({ max_price: 30000, min_size_m2: 40, dispositions: ['1+kk', '2+kk'] });
		for (const card of exampleListings(limited)) {
			expect(card.price).toBeLessThanOrEqual(30000);
			expect(card.size).toBeGreaterThanOrEqual(40);
			expect(['1+kk', '2+kk']).toContain(card.layout);
		}
	});

	test('marks a target no listing the search allows comes near', () => {
		const cards = exampleListings(profile({ max_price: 30000, min_size_m2: 40 }));
		expect(cards.map((card) => [card.target, card.nearTarget])).toEqual([
			[100, true],
			[10, false]
		]);
	});

	test('keeps only the lower target when two fall on one listing', () => {
		const cards = exampleListings(profile({ max_price: 30000, min_size_m2: 40 }));
		const scores = cards.map((card) => card.score);
		expect(new Set(scores).size).toBe(scores.length);
		expect(cards.map((card) => card.target)).not.toContain(50);
	});

	test('gives land no size or layout and a flat no land', () => {
		const land = exampleListings({
			...FLAT_TO_RENT,
			criteria: { ...FLAT_TO_RENT.criteria, estate_type: 'land', offer_type: 'sale' },
			preferredValues: { ...FLAT_TO_RENT.preferredValues, preferred_land_m2: 800 }
		});
		for (const card of land) expect(card).toMatchObject({ size: null, layout: null });
		for (const card of exampleListings(FLAT_TO_RENT)) expect(card.land).toBeNull();
	});
});
