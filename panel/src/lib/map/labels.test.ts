import { describe, expect, test } from 'vitest';
import { placeLabels, textBox, type RegionLabel, type TownLabel } from './labels';

const SIZES = { region: 10, town: 10, gap: 1 };

function town(key: string, x: number, y: number, streets = 10): TownLabel {
	return { key, text: key, x, y, radius: 2, streets };
}

describe('textBox', () => {
	test('spans the text to either side of its anchor', () => {
		expect(textBox(100, 50, 'abcd', 10, 'middle')).toEqual({ x0: 88, y0: 44, x1: 112, y1: 56 });
		expect(textBox(100, 50, 'abcd', 10, 'start')).toEqual({ x0: 100, y0: 44, x1: 124, y1: 56 });
		expect(textBox(100, 50, 'abcd', 10, 'end')).toEqual({ x0: 76, y0: 44, x1: 100, y1: 56 });
	});
});

describe('placeLabels', () => {
	test('keeps a region name on its spot when nothing is in the way', () => {
		const { regions } = placeLabels([{ key: 'a', text: 'Kolín', x: 100, y: 100 }], [], SIZES);
		expect(regions).toEqual([{ key: 'a', text: 'Kolín', x: 100, y: 100, anchor: 'middle' }]);
	});

	test('moves a region name that would cover an earlier one', () => {
		const regions: RegionLabel[] = [
			{ key: 'a', text: 'Brno-město', x: 100, y: 100 },
			{ key: 'b', text: 'Brno-venkov', x: 100, y: 100 }
		];
		const placed = placeLabels(regions, [], SIZES).regions;
		expect(placed[0].y).toBe(100);
		expect(placed[1].y).toBe(112);
	});

	test('keeps a region name on its spot when every spot is taken', () => {
		const regions = [0, 1, 2, 3, 4, 5].map((i) => ({ key: `r${i}`, text: 'Praha', x: 100, y: 100 }));
		expect(placeLabels(regions, [], SIZES).regions[5].y).toBe(100);
	});

	test('names a town above its dot', () => {
		const { towns } = placeLabels([], [town('Kdyně', 100, 100)], SIZES);
		expect(towns).toEqual([{ key: 'Kdyně', text: 'Kdyně', x: 100, y: 91, anchor: 'middle' }]);
	});

	test('falls back below, then right, then left, around the dot', () => {
		// Each blocker covers one spot around the dot at 100, 100 and no other.
		const above: RegionLabel = { key: 'above', text: 'xxxxxxxxxx', x: 100, y: 86 };
		const below: RegionLabel = { key: 'below', text: 'xxxxxxxxxx', x: 100, y: 114 };
		const right: RegionLabel = { key: 'right', text: 'xx', x: 110, y: 100 };
		const placedWith = (blockers: RegionLabel[]) => placeLabels(blockers, [town('A', 100, 100)], SIZES).towns[0];
		expect([placedWith([above]).y, placedWith([above]).anchor]).toEqual([109, 'middle']);
		expect([placedWith([above, below]).x, placedWith([above, below]).anchor]).toEqual([103, 'start']);
		expect([placedWith([above, below, right]).x, placedWith([above, below, right]).anchor]).toEqual([97, 'end']);
	});

	test('leaves a town unnamed when every spot around it is taken', () => {
		// Two wide names just above and below the dot cover all four spots.
		const walls = [91, 109].map((y) => ({ key: `wall ${y}`, text: 'x'.repeat(40), x: 100, y }));
		expect(placeLabels(walls, [town('A', 100, 100)], SIZES).towns).toEqual([]);
	});

	test('gives the shared spot to the bigger of two crowded towns', () => {
		const towns = [town('Small', 100, 100, 5), town('Big', 104, 100, 500)];
		const placed = placeLabels([], towns, SIZES).towns;
		expect(placed.find((label) => label.key === 'Big')?.y).toBe(91);
		expect(placed.find((label) => label.key === 'Small')?.y).toBe(109);
	});

	test("keeps a name off another town's dot", () => {
		const towns = [town('A', 100, 100, 500), town('B', 100, 91, 5)];
		expect(placeLabels([], towns, SIZES).towns.find((label) => label.key === 'A')?.y).toBe(109);
	});
});
