import { describe, expect, test } from 'vitest';
import { listing } from '$lib/test-support/listing';
import { naturalOrder, sortListings, type ListingOrder } from './listing-order';

const OLD = listing('a', { first_seen_at: '2026-10-01T00:00:00Z', price: 25000, size_m2: 50 });
const MIDDLE = listing('b', { first_seen_at: '2026-10-02T00:00:00Z', price: 18000, size_m2: 70 });
const RECENT = listing('c', { first_seen_at: '2026-10-03T00:00:00Z', price: null, size_m2: 40 });
const SCORES: Record<string, number> = { a: 80, b: 40, c: 60 };

function ids(order: ListingOrder): string[] {
	const sorted = sortListings(
		[OLD, MIDDLE, RECENT],
		order,
		(each) => SCORES[each.id],
		(each) => each.first_seen_at
	);
	return sorted.map((each) => each.id);
}

describe('naturalOrder', () => {
	test('puts the best score, the newest and the largest first, the cheapest first', () => {
		expect(['score', 'date', 'size', 'price', 'pricePerM2'].map((field) => naturalOrder(field as never).descending)).toEqual(
			[true, true, true, false, false]
		);
	});
});

describe('sortListings', () => {
	test('orders by score, either way', () => {
		expect(ids({ field: 'score', descending: true })).toEqual(['a', 'c', 'b']);
		expect(ids({ field: 'score', descending: false })).toEqual(['b', 'c', 'a']);
	});

	test('orders by date, either way', () => {
		expect(ids({ field: 'date', descending: true })).toEqual(['c', 'b', 'a']);
		expect(ids({ field: 'date', descending: false })).toEqual(['a', 'b', 'c']);
	});

	test('orders by size', () => {
		expect(ids({ field: 'size', descending: true })).toEqual(['b', 'a', 'c']);
	});

	test('keeps a listing missing the field last, either way', () => {
		expect(ids({ field: 'price', descending: false })).toEqual(['b', 'a', 'c']);
		expect(ids({ field: 'price', descending: true })).toEqual(['a', 'b', 'c']);
	});

	test('orders by price per m²', () => {
		expect(ids({ field: 'pricePerM2', descending: false })).toEqual(['b', 'a', 'c']);
	});

	test('breaks a tie newest first', () => {
		const twin = listing('d', { first_seen_at: '2026-10-04T00:00:00Z', price: 25000, size_m2: 50 });
		const sorted = sortListings([OLD, twin], { field: 'price', descending: false }, () => null, (each) => each.first_seen_at);
		expect(sorted.map((each) => each.id)).toEqual(['d', 'a']);
	});
});
