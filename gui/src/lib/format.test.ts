import { describe, expect, test } from 'vitest';
import { daysSince, formatPrice, formatPricePerM2 } from './format';

describe('formatPrice', () => {
	test('groups thousands with a non-breaking space and appends Kč', () => {
		expect(formatPrice(25000)).toBe('25 000 Kč');
	});

	test('leaves a sub-thousand price ungrouped', () => {
		expect(formatPrice(500)).toBe('500 Kč');
	});
});

describe('formatPricePerM2', () => {
	test('rounds price divided by size and appends Kč/m²', () => {
		expect(formatPricePerM2(21000, 52)).toBe('404 Kč/m²');
	});

	test('returns null for a zero or negative size', () => {
		expect(formatPricePerM2(21000, 0)).toBeNull();
		expect(formatPricePerM2(21000, -5)).toBeNull();
	});
});

describe('daysSince', () => {
	test('is zero for a timestamp from today', () => {
		const now = new Date('2026-09-19T12:00:00Z');
		expect(daysSince('2026-09-19T08:00:00Z', now)).toBe(0);
	});

	test('counts whole days elapsed', () => {
		const now = new Date('2026-09-19T12:00:00Z');
		expect(daysSince('2026-09-15T12:00:00Z', now)).toBe(4);
	});
});
