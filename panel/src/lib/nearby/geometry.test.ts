import { describe, expect, test } from 'vitest';
import { boxAround, distanceM, nearest } from './geometry';

const VLTAVSKA = { lat: 50.1002, lon: 14.4385 };
const FLORENC = { lat: 50.0902, lon: 14.4393 };

describe('distanceM', () => {
	test('measures the straight line between two points in metres', () => {
		expect(distanceM(VLTAVSKA, FLORENC)).toBeCloseTo(1113, -1);
	});

	test('is nothing between a point and itself', () => {
		expect(distanceM(VLTAVSKA, VLTAVSKA)).toBe(0);
	});
});

describe('nearest', () => {
	test('finds the closest place and how far it is', () => {
		const flat = { lat: 50.099, lon: 14.439 };
		const found = nearest(flat, [
			{ name: 'Florenc', point: FLORENC },
			{ name: 'Vltavská', point: VLTAVSKA }
		]);
		expect(found?.place.name).toBe('Vltavská');
		expect(found?.distanceM).toBeCloseTo(distanceM(flat, VLTAVSKA));
	});

	test('finds nothing among no places', () => {
		expect(nearest(VLTAVSKA, [])).toBeNull();
	});
});

describe('boxAround', () => {
	test('grows the box around the points by the margin on every side', () => {
		const box = boxAround([VLTAVSKA, FLORENC], 1000);
		expect(box).not.toBeNull();
		expect(distanceM({ lat: box!.north, lon: VLTAVSKA.lon }, { lat: VLTAVSKA.lat, lon: VLTAVSKA.lon })).toBeCloseTo(1000, -1);
		expect(distanceM({ lat: FLORENC.lat, lon: box!.west }, { lat: FLORENC.lat, lon: VLTAVSKA.lon })).toBeCloseTo(1000, -1);
	});

	test('is no box around no points', () => {
		expect(boxAround([], 1000)).toBeNull();
	});
});
