import { describe, expect, test } from 'vitest';
import { trackedProperty } from '$lib/test-support/tracked-property';
import {
	activeFacets,
	layoutsAmong,
	noFilter,
	passes,
	portalsAmong,
	scaleAmong,
	withoutFacet,
	type PropertyFilter
} from './property-filter';

function filtered(changes: Partial<PropertyFilter>): PropertyFilter {
	return { ...noFilter(), ...changes };
}

describe('passes', () => {
	test('lets every listing through an empty filter', () => {
		expect(passes(trackedProperty('a', { price: null, size_m2: null }), noFilter(), null)).toBe(true);
	});

	test('keeps only the chosen portals and layouts', () => {
		const flat = trackedProperty('sreality:1', { source: 'sreality', disposition: '2+kk' });
		expect(passes(flat, filtered({ portals: ['sreality', 'remax'] }), null)).toBe(true);
		expect(passes(flat, filtered({ portals: ['remax'] }), null)).toBe(false);
		expect(passes(flat, filtered({ layouts: ['3+1'] }), null)).toBe(false);
	});

	test('keeps only price drops when asked', () => {
		const filter = filtered({ onlyPriceDrops: true });
		expect(passes(trackedProperty('a', { price_drop_from: 25000 }), filter, null)).toBe(true);
		expect(passes(trackedProperty('b', { price_drop_from: null }), filter, null)).toBe(false);
	});

	test('keeps a score at or above the minimum, and no unscored listing', () => {
		const filter = filtered({ minimumScore: 60 });
		expect(passes(trackedProperty('a'), filter, 60)).toBe(true);
		expect(passes(trackedProperty('a'), filter, 59)).toBe(false);
		expect(passes(trackedProperty('a'), filter, null)).toBe(false);
	});

	test('keeps a value within its bounds, either bound open', () => {
		const flat = trackedProperty('a', { price: 20000, size_m2: 55 });
		expect(passes(flat, filtered({ minPrice: 20000, maxPrice: 20000 }), null)).toBe(true);
		expect(passes(flat, filtered({ maxPrice: 19999 }), null)).toBe(false);
		expect(passes(flat, filtered({ minSize: 56 }), null)).toBe(false);
	});

	test('lets no listing lacking a fact through a bound on it', () => {
		expect(passes(trackedProperty('a', { land_m2: null }), filtered({ minLand: 100 }), null)).toBe(false);
	});
});

describe('facets', () => {
	test('names each part of the filter in use', () => {
		const filter = filtered({ portals: ['remax'], onlyPriceDrops: true, maxPrice: 20000, minLand: 300 });
		expect(activeFacets(filter)).toEqual(['portals', 'priceDrops', 'price', 'land']);
		expect(activeFacets(noFilter())).toEqual([]);
	});

	test('clears one part and keeps the rest', () => {
		const filter = filtered({ onlyPriceDrops: true, minPrice: 15000, maxPrice: 20000 });
		expect(withoutFacet(filter, 'price')).toEqual(filtered({ onlyPriceDrops: true }));
	});
});

describe('what the listings offer', () => {
	const listings = [
		trackedProperty('remax:1', { source: 'remax', disposition: '3+1', price: 18400 }),
		trackedProperty('sreality:1', { source: 'sreality', disposition: '2+kk', price: 29700 }),
		trackedProperty('sreality:2', { source: 'sreality', disposition: '2+kk', price: null })
	];

	test('lists the portals and layouts present, in the app’s order', () => {
		expect(portalsAmong(listings)).toEqual(['sreality', 'remax']);
		expect(layoutsAmong(listings)).toEqual(['2+kk', '3+1']);
	});

	test('spans a scale from the lowest to the highest value, rounded outwards', () => {
		const scale = scaleAmong(listings, (each) => each.price, 500)!;
		expect(scale.valueAt(0)).toBe(18000);
		expect(scale.valueAt(scale.lastIndex)).toBe(30000);
		expect(scale.stops.every((stop) => stop % 500 === 0)).toBe(true);
	});

	test('offers no scale when the listings do not differ', () => {
		expect(scaleAmong([trackedProperty('a', { size_m2: 50 }), trackedProperty('b', { size_m2: 50 })], (each) => each.size_m2, 5)).toBeNull();
		expect(scaleAmong([trackedProperty('a', { land_m2: null })], (each) => each.land_m2, 50)).toBeNull();
	});
});
