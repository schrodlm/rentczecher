import { describe, expect, test } from 'vitest';
import type { PostingPricesModel } from '$lib/api/client';
import { priceChartOf, type PlotBox } from './price-history';

const BOX: PlotBox = { width: 100, height: 50, marginX: 0, marginY: 0 };

function posting(listingId: string, changes: [number, string, string][]): PostingPricesModel {
	return {
		listing_id: listingId,
		source: listingId.split(':')[0],
		url: `https://example.invalid/${listingId}`,
		changes: changes.map(([price, first_seen_at, last_seen_at]) => ({ price, charges: null, first_seen_at, last_seen_at }))
	};
}

describe('priceChartOf', () => {
	test('steps each price across the time it held until the next was first seen', () => {
		const chart = priceChartOf(
			[
				posting('sreality:1', [
					[20000, '2026-10-01T00:00:00Z', '2026-10-02T00:00:00Z'],
					[18000, '2026-10-03T00:00:00Z', '2026-10-05T00:00:00Z']
				])
			],
			'sreality:1',
			BOX
		)!;
		expect(chart.lowest).toBe(18000);
		expect(chart.highest).toBe(20000);
		expect(chart.since).toBe('2026-10-01T00:00:00Z');
		expect(chart.until).toBe('2026-10-05T00:00:00Z');
		expect(chart.lines[0].path).toBe('M0,0 L50,0 L50,50 L100,50');
		expect(chart.lines[0]).toMatchObject({ own: true, endX: 100, endY: 50, current: 18000 });
	});

	test('puts every posting on one scale, marking the listing’s own wherever it comes', () => {
		const chart = priceChartOf(
			[
				posting('bezrealitky:1', [[24000, '2026-10-01T00:00:00Z', '2026-10-05T00:00:00Z']]),
				posting('sreality:1', [[26000, '2026-10-03T00:00:00Z', '2026-10-05T00:00:00Z']])
			],
			'sreality:1',
			BOX
		)!;
		const [other, own] = chart.lines;
		expect(other).toMatchObject({ listingId: 'bezrealitky:1', own: false, endY: 50 });
		expect(own).toMatchObject({ listingId: 'sreality:1', source: 'sreality', own: true, endY: 0 });
		expect(own.path).toBe('M50,0 L100,0');
	});

	test('draws an unchanged price level through the middle', () => {
		const chart = priceChartOf([posting('remax:1', [[19500, '2026-10-01T00:00:00Z', '2026-10-05T00:00:00Z']])], 'remax:1', BOX)!;
		expect(chart.lowest).toBe(chart.highest);
		expect(chart.lines[0].path).toBe('M0,25 L100,25');
	});

	test('charts nothing until some posting has a price', () => {
		expect(priceChartOf([], 'sreality:1', BOX)).toBeNull();
		expect(priceChartOf([posting('sreality:1', [])], 'sreality:1', BOX)).toBeNull();
	});
});
