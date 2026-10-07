import { describe, expect, test } from 'vitest';
import map from './czech-map.json';

const regions = [...map.kraje, ...map.okresy, ...map.obvody];

describe('the map of Czechia', () => {
	test('holds every kraj, okres with Praha, and Praha obvod', () => {
		expect(map.kraje).toHaveLength(14);
		expect(map.okresy).toHaveLength(77);
		expect(map.obvody).toHaveLength(10);
	});

	test.each(regions.map((region) => [region.kind, region.name, region] as const))(
		'gives %s %s an outline with its label inside its box',
		(_kind, _name, region) => {
			expect(region.path).toMatch(/^M[\d.,L]+Z/);
			const [x0, y0, x1, y1] = region.bbox;
			const [x, y] = region.label;
			expect(x).toBeGreaterThanOrEqual(x0);
			expect(x).toBeLessThanOrEqual(x1);
			expect(y).toBeGreaterThanOrEqual(y0);
			expect(y).toBeLessThanOrEqual(y1);
		}
	);

	test('places every town in an okres of its own kraj', () => {
		const okresy = new Map(map.okresy.map((okres) => [`${okres.kind}:${okres.code}`, okres]));
		for (const town of map.obce) {
			expect(okresy.get(`okres:${town.okres}`)?.kraj).toBe(town.kraj);
		}
	});
});
