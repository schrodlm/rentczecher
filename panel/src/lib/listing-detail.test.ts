import { describe, expect, test } from 'vitest';
import { listing } from '$lib/test-support/listing';
import { historyOf, percentAbove, percentBelow, percentFromMiddle, pricePerM2, standingOf } from './listing-detail';

const CHEAP = listing('a', { price: 18000, size_m2: 40 });
const MIDDLE = listing('b', { price: 22000, size_m2: 55 });
const DEAR = listing('c', { price: 30000, size_m2: 60 });
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
		expect(standingOf(listing('d', { price: null }), PROFILE, (each) => each.price)).toBeNull();
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

describe('historyOf', () => {
	test('lists what happened newest first, an undated drop just after the finding', () => {
		const events = historyOf(
			listing('a', {
				first_seen_at: '2026-10-01T00:00:00Z',
				viewed_at: '2026-10-03T00:00:00Z',
				favourited_at: '2026-10-05T00:00:00Z',
				price: 18000,
				price_drop_from: 20000
			})
		);
		expect(events.map((event) => event.kind)).toEqual(['favourite', 'viewed', 'priceDrop', 'found']);
		expect(events[2]).toEqual({ kind: 'priceDrop', at: null, from: 20000, to: 18000 });
	});

	test('lists only the finding of a listing nothing else happened to', () => {
		expect(historyOf(listing('a', { first_seen_at: '2026-10-01T00:00:00Z' }))).toEqual([
			{ kind: 'found', at: '2026-10-01T00:00:00Z' }
		]);
	});
});
