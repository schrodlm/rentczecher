import type { NamedPlace } from '$lib/api/client';
import data from './czech-map.json';

/* A kraj, an okres or a Praha obvod as drawn: its outline, the box the map
zooms to, and where its name goes. */
export type Region = {
	kind: 'kraj' | 'okres' | 'obec' | 'obvod';
	code: number;
	name: string;
	path: string;
	bbox: [x0: number, y0: number, x1: number, y1: number];
	label: [x: number, y: number];
};
/* An okres, or Praha, which lies in no okres and is drawn as an obec among
them. */
export type District = Region & { kraj: number };
export type Town = { code: number; name: string; okres: number; kraj: number; x: number; y: number; streets: number };

type CzechMap = {
	width: number;
	height: number;
	kraje: Region[];
	okresy: District[];
	obvody: Region[];
	obce: Town[];
};

// JSON types its kinds as plain strings and its boxes as lists of any length,
// so the shape cannot be checked here. The map's tests pin it.
const czechMap = data as unknown as CzechMap;

export const MAP_WIDTH = czechMap.width;
export const MAP_HEIGHT = czechMap.height;
export const KRAJE = czechMap.kraje;
export const OBVODY = czechMap.obvody;
export const TOWNS = czechMap.obce;
const DISTRICTS = czechMap.okresy;

const PRAHA_KRAJ = 19;
const PRAHA_OBEC = 554782;
const STREDOCESKY_KRAJ = 27;

export const PRAHA = DISTRICTS.find((district) => district.kind === 'obec' && district.code === PRAHA_OBEC)!;

export function isPraha(kraj: Region): boolean {
	return kraj.code === PRAHA_KRAJ;
}

export function krajByCode(code: number): Region | null {
	return KRAJE.find((kraj) => kraj.code === code) ?? null;
}

export function krajOf(district: District): Region {
	return krajByCode(district.kraj)!;
}

/* The districts of a kraj, with Praha among Středočeský's, since Praha is a
kraj of its own in the middle of it. */
export function districtsOf(kraj: Region): District[] {
	const own = DISTRICTS.filter((district) => district.kraj === kraj.code);
	return kraj.code === STREDOCESKY_KRAJ ? [...own, PRAHA] : own;
}

/* The district a place picked by name lies in, found by its okres name since
the map holds only the bigger towns. None for a kraj, which no district
holds, or a place the map cannot place. */
export function districtOf(place: NamedPlace): District | null {
	if (place.kind === 'kraj') return null;
	if (place.kind === 'okres') {
		return DISTRICTS.find((district) => district.kind === 'okres' && district.code === place.code) ?? null;
	}
	if (place.obec === 'Praha' || (place.kind === 'obec' && place.code === PRAHA_OBEC)) return PRAHA;
	return DISTRICTS.find((district) => district.kind === 'okres' && district.name === place.okres) ?? null;
}
