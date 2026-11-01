import { beforeAll, describe, expect, test } from 'vitest';
import type { PostingPricesModel, TrackedPropertyModel } from '$lib/api/client';
import { Translator } from '$lib/i18n/translator';
import { trackedProperty } from '$lib/test-support/tracked-property';
import {
	changesSince,
	factsOf,
	historyOf,
	isHighest,
	isLowest,
	percentAbove,
	percentBelow,
	percentFromMiddle,
	placeOf,
	pricePerM2,
	standingOf
} from './property-detail';

const CHEAP = trackedProperty('a', { price: 18000, size_m2: 40 });
const MIDDLE = trackedProperty('b', { price: 22000, size_m2: 55 });
const DEAR = trackedProperty('c', { price: 30000, size_m2: 60 });
const PROFILE = [CHEAP, MIDDLE, DEAR];

describe('standingOf', () => {
	test("places the listing's fact among the others'", () => {
		expect(standingOf(MIDDLE, PROFILE, (each) => each.price)).toEqual({
			own: 22000,
			others: [18000, 30000],
			lowest: 18000,
			highest: 30000,
			middle: 24000
		});
	});

	test('takes the middle from the other listings alone', () => {
		expect(standingOf(DEAR, PROFILE, (each) => each.price)?.middle).toBe(20000);
	});

	test('stands nowhere without the fact or another listing', () => {
		expect(standingOf(trackedProperty('d', { price: null }), PROFILE, (each) => each.price)).toBeNull();
		expect(standingOf(CHEAP, [CHEAP], (each) => each.price)).toBeNull();
	});
});

describe('percentages', () => {
	test('count the other listings below and above, never the listing itself', () => {
		const price = standingOf(MIDDLE, PROFILE, (each) => each.price)!;
		expect(percentBelow(price)).toBe(50);
		expect(percentAbove(price)).toBe(50);
	});

	test('measure from the middle of the others', () => {
		expect(percentFromMiddle(standingOf(DEAR, PROFILE, (each) => each.price)!)).toBe(50);
		expect(percentFromMiddle(standingOf(MIDDLE, PROFILE, pricePerM2)!)).toBe(-16);
	});
});

describe('extremes', () => {
	test('count only a value every other listing lies strictly beyond', () => {
		const many = [CHEAP, MIDDLE, ...Array.from({ length: 250 }, (_, index) => trackedProperty(`d${index}`, { price: 30000 }))];
		const nearlyCheapest = standingOf(MIDDLE, many, (each) => each.price)!;
		expect(percentAbove(nearlyCheapest)).toBe(100);
		expect(isLowest(nearlyCheapest)).toBe(false);
		expect(isLowest(standingOf(CHEAP, many, (each) => each.price)!)).toBe(true);
	});

	test('leave a value tied with every other listing at neither end', () => {
		const tied = [trackedProperty('a', { price: 20000 }), trackedProperty('b', { price: 20000 })];
		const standing = standingOf(tied[0], tied, (each) => each.price)!;
		expect(isLowest(standing)).toBe(false);
		expect(isHighest(standing)).toBe(false);
	});
});

describe('factsOf', () => {
	let t: Translator;
	beforeAll(async () => {
		t = await Translator.load('cs');
	});

	test('joins the layout and the formatted size, leaving the place to the name', () => {
		const flat = trackedProperty('a', { disposition: '2+kk', size_m2: 1200, location_raw_text: 'Praha 7' });
		expect(factsOf(flat, t).replace(/\s/g, ' ')).toBe('2+kk · 1 200 m²');
	});

	test('names an atypical layout and leaves out what the listing lacks', () => {
		const flat = trackedProperty('a', { disposition: 'atypicky', size_m2: null, location_raw_text: null });
		expect(factsOf(flat, t)).toBe('atypická dispozice');
	});
});

function located(places: Partial<NonNullable<TrackedPropertyModel['resolved_location']>>) {
	return trackedProperty('a', {
		resolved_location: {
			kraj: { code: 19, name: 'Hlavní město Praha' },
			okres: null,
			obec: null,
			obvod: null,
			mestska_cast: null,
			cast_obce: null,
			ulice: null,
			cislo_popisne: null,
			cislo_orientacni: null,
			...places
		}
	});
}

describe('placeOf', () => {
	test('names the street and the part of town', () => {
		const flat = located({ ulice: { code: 1, name: 'Přístavní' }, cast_obce: { code: 2, name: 'Holešovice' } });
		expect(placeOf(flat)).toBe('Přístavní, Holešovice');
	});

	test('names the part of town and the district without a street', () => {
		const flat = located({ cast_obce: { code: 2, name: 'Holešovice' }, obvod: { code: 78, name: 'Praha 7' } });
		expect(placeOf(flat)).toBe('Holešovice, Praha 7');
	});

	test('names a place once when its part of town shares its name', () => {
		const flat = located({
			cast_obce: { code: 3, name: 'Nekvasovy' },
			obec: { code: 4, name: 'Nekvasovy' },
			okres: { code: 5, name: 'Plzeň-jih' }
		});
		expect(placeOf(flat)).toBe('Nekvasovy, Plzeň-jih');
	});

	test("falls back to the portal's own words while the place is not known", () => {
		expect(placeOf(trackedProperty('a', { resolved_location: null, location_raw_text: 'Praha 7, Holešovice' }))).toBe(
			'Praha 7, Holešovice'
		);
	});
});

describe('historyOf', () => {
	const OWN_PRICES: PostingPricesModel = {
		listing_id: 'a',
		source: 'sreality',
		url: 'https://example.invalid/a',
		changes: [
			{ price: 20000, charges: null, first_seen_at: '2026-10-01T00:00:00Z', last_seen_at: '2026-10-02T00:00:00Z' },
			{ price: 18000, charges: null, first_seen_at: '2026-10-04T00:00:00Z', last_seen_at: '2026-10-06T00:00:00Z' },
			{ price: 19000, charges: null, first_seen_at: '2026-10-07T00:00:00Z', last_seen_at: '2026-10-07T00:00:00Z' }
		]
	};
	const OTHER_PRICES: PostingPricesModel = {
		listing_id: 'b',
		source: 'remax',
		url: 'https://example.invalid/b',
		changes: [
			{ price: 30000, charges: null, first_seen_at: '2026-10-01T00:00:00Z', last_seen_at: '2026-10-01T00:00:00Z' },
			{ price: 10000, charges: null, first_seen_at: '2026-10-02T00:00:00Z', last_seen_at: '2026-10-02T00:00:00Z' }
		]
	};

	test('lists what happened newest first, each price change of each posting dated', () => {
		const events = historyOf(
			trackedProperty('a', {
				first_seen_at: '2026-10-01T00:00:00Z',
				viewed_at: '2026-10-03T00:00:00Z',
				favourited_at: '2026-10-05T00:00:00Z'
			}),
			[OTHER_PRICES, OWN_PRICES]
		);
		expect(events).toEqual([
			{ kind: 'priceChange', at: '2026-10-07T00:00:00Z', from: 18000, to: 19000, source: null },
			{ kind: 'favourite', at: '2026-10-05T00:00:00Z' },
			{ kind: 'priceChange', at: '2026-10-04T00:00:00Z', from: 20000, to: 18000, source: null },
			{ kind: 'viewed', at: '2026-10-03T00:00:00Z' },
			{ kind: 'priceChange', at: '2026-10-02T00:00:00Z', from: 30000, to: 10000, source: 'remax' },
			{ kind: 'found', at: '2026-10-01T00:00:00Z' }
		]);
	});

	test('dates when another portal started posting the flat after it was first found', () => {
		const events = historyOf(trackedProperty('a', { first_seen_at: '2026-10-01T00:00:00Z' }), [
			OWN_PRICES,
			{
				listing_id: 'c',
				source: 'idnes',
				url: 'https://example.invalid/c',
				changes: [{ price: 19500, charges: null, first_seen_at: '2026-10-06T00:00:00Z', last_seen_at: '2026-10-06T00:00:00Z' }]
			}
		]);
		expect(events).toContainEqual({ kind: 'posted', at: '2026-10-06T00:00:00Z', source: 'idnes' });
	});

	test('does not count a posting found with the flat as posted later', () => {
		const events = historyOf(trackedProperty('a', { first_seen_at: '2026-10-01T00:00:00Z' }), [OWN_PRICES, OTHER_PRICES]);
		expect(events.some((event) => event.kind === 'posted')).toBe(false);
	});

	test('lists no price change until the prices are known', () => {
		expect(historyOf(trackedProperty('a', { first_seen_at: '2026-10-01T00:00:00Z', price_drop_from: 25000 }), null)).toEqual([
			{ kind: 'found', at: '2026-10-01T00:00:00Z' }
		]);
	});
});

describe('changesSince', () => {
	test('keeps the new portals and new prices after the time, and nothing else', () => {
		const changes = changesSince(
			[
				{ kind: 'priceChange', at: '2026-10-07T00:00:00Z', from: 18000, to: 19000, source: null },
				{ kind: 'posted', at: '2026-10-06T00:00:00Z', source: 'idnes' },
				{ kind: 'favourite', at: '2026-10-05T00:00:00Z' },
				{ kind: 'priceChange', at: '2026-10-02T00:00:00Z', from: 20000, to: 18000, source: null },
				{ kind: 'viewed', at: '2026-10-03T00:00:00Z' },
				{ kind: 'found', at: '2026-10-01T00:00:00Z' }
			],
			'2026-10-03T00:00:00Z'
		);
		expect(changes).toEqual([
			{ kind: 'priceChange', at: '2026-10-07T00:00:00Z', from: 18000, to: 19000, source: null },
			{ kind: 'posted', at: '2026-10-06T00:00:00Z', source: 'idnes' }
		]);
	});
});
