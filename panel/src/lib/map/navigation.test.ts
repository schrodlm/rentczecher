import { describe, expect, test } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { KRAJE, PRAHA, districtsOf, krajByCode, MAP_HEIGHT, MAP_WIDTH } from './czech-map';
import { MapNavigation } from './navigation.svelte';

const PLZENSKY = krajByCode(43)!;
const STREDOCESKY = krajByCode(27)!;
const HLAVNI_MESTO_PRAHA = krajByCode(19)!;
const DOMAZLICE = districtsOf(PLZENSKY).find((district) => district.name === 'Domažlice')!;

function place(kind: NamedPlace['kind'], code: number, names: Partial<NamedPlace> = {}): NamedPlace {
	return { kind, code, name: null, obec: null, okres: null, ...names };
}

describe('MapNavigation over the whole country', () => {
	test('shows every kraj by name and only the biggest cities', () => {
		const navigation = new MapNavigation();
		expect(navigation.namedRegions).toBe(KRAJE);
		expect(navigation.districts).toEqual([]);
		expect(navigation.towns.map((town) => town.name)).toContain('Brno');
		expect(navigation.towns.every((town) => town.streets >= 400)).toBe(true);
	});

	test('shows the whole map and has nowhere to go back to', () => {
		const navigation = new MapNavigation();
		expect(navigation.view).toEqual({ x: 0, y: 0, width: MAP_WIDTH, height: MAP_HEIGHT });
		expect(navigation.regionInView).toBeNull();
		expect(navigation.canGoBack).toBe(false);
	});
});

describe('MapNavigation in a kraj', () => {
	test('shows its districts by name and its eight biggest towns', () => {
		const navigation = new MapNavigation();
		navigation.openKraj(PLZENSKY);
		expect(navigation.kraj).toBe(PLZENSKY);
		expect(navigation.namedRegions).toEqual(districtsOf(PLZENSKY));
		expect(navigation.towns).toHaveLength(8);
		expect(navigation.towns.every((town) => town.kraj === 43)).toBe(true);
		expect(navigation.regionInView).toBe(PLZENSKY);
	});

	test('zooms to a box around the kraj in the map’s proportions', () => {
		const navigation = new MapNavigation();
		navigation.openKraj(PLZENSKY);
		const { x, y, width, height } = navigation.view;
		const [x0, y0, x1, y1] = PLZENSKY.bbox;
		expect(x).toBeLessThan(x0);
		expect(y).toBeLessThan(y0);
		expect(x + width).toBeGreaterThan(x1);
		expect(y + height).toBeGreaterThan(y1);
		expect(width / height).toBeCloseTo(MAP_WIDTH / MAP_HEIGHT);
	});

	test('counts Praha among Středočeský’s districts', () => {
		const navigation = new MapNavigation();
		navigation.openKraj(STREDOCESKY);
		expect(navigation.districts).toContain(PRAHA);
	});
});

describe('MapNavigation in a district', () => {
	test('shows the okres’s twelve main towns and names none of its regions', () => {
		const navigation = new MapNavigation();
		navigation.openKraj(PLZENSKY);
		navigation.openDistrict(DOMAZLICE);
		expect(navigation.district).toBe(DOMAZLICE);
		expect(navigation.kraj).toBe(PLZENSKY);
		expect(navigation.towns).toHaveLength(12);
		expect(navigation.towns.every((town) => town.okres === DOMAZLICE.code)).toBe(true);
		expect(navigation.namedRegions).toEqual([]);
	});

	test('opens Praha straight to its obvody, from the country', () => {
		const navigation = new MapNavigation();
		navigation.openKraj(HLAVNI_MESTO_PRAHA);
		expect(navigation.district).toBe(PRAHA);
		expect(navigation.inPraha).toBe(true);
		expect(navigation.obvody).toHaveLength(10);
		expect(navigation.namedRegions).toHaveLength(10);
		expect(navigation.towns).toEqual([]);
	});
});

describe('MapNavigation going back', () => {
	test('retraces the steps it took', () => {
		const navigation = new MapNavigation();
		navigation.openKraj(STREDOCESKY);
		navigation.openDistrict(PRAHA);
		navigation.back();
		expect(navigation.kraj).toBe(STREDOCESKY);
		expect(navigation.district).toBeNull();
		navigation.back();
		expect(navigation.kraj).toBeNull();
		expect(navigation.canGoBack).toBe(false);
	});

	test('does not count opening the region already in view as a step', () => {
		const navigation = new MapNavigation();
		navigation.openKraj(PLZENSKY);
		navigation.openKraj(PLZENSKY);
		navigation.back();
		expect(navigation.kraj).toBeNull();
		expect(navigation.canGoBack).toBe(false);
	});

	test('forgets the way back on returning to the whole country', () => {
		const navigation = new MapNavigation();
		navigation.openKraj(PLZENSKY);
		navigation.openDistrict(DOMAZLICE);
		navigation.openCountry();
		expect(navigation.canGoBack).toBe(false);
		navigation.back();
		expect(navigation.kraj).toBeNull();
	});
});

describe('MapNavigation showing a place picked by name', () => {
	test.each([
		['a kraj', place('kraj', 43), PLZENSKY, null],
		['an okres', place('okres', DOMAZLICE.code), PLZENSKY, DOMAZLICE],
		['a village the map does not draw', place('obec', 1, { okres: 'Domažlice' }), PLZENSKY, DOMAZLICE],
		['a street outside Praha', place('ulice', 1, { obec: 'Kdyně', okres: 'Domažlice' }), PLZENSKY, DOMAZLICE],
		['Praha itself', place('obec', 554782), HLAVNI_MESTO_PRAHA, PRAHA],
		['a part of Praha', place('cast_obce', 490067, { obec: 'Praha' }), HLAVNI_MESTO_PRAHA, PRAHA]
	])('brings %s into view', (_what, picked, kraj, district) => {
		const navigation = new MapNavigation();
		navigation.show(picked);
		expect(navigation.kraj).toBe(kraj);
		expect(navigation.district).toBe(district);
	});

	test('stays put for a place it cannot place', () => {
		const navigation = new MapNavigation();
		navigation.show(place('obec', 1));
		expect(navigation.regionInView).toBeNull();
	});
});
