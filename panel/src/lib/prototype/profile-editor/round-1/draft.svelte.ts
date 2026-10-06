/* PROTOTYPE, throwaway. Round 1's draft, kept so its variants still build. */

import type { components } from '$lib/api/types.gen';

export type NamedPlace = components['schemas']['NamedPlaceModel'];
export type Portal = 'sreality' | 'bezrealitky' | 'remax';

export const PORTALS: Portal[] = ['sreality', 'bezrealitky', 'remax'];
export const PORTAL_LABEL: Record<Portal, string> = {
	sreality: 'Sreality',
	bezrealitky: 'Bezrealitky',
	remax: 'RE/MAX'
};

export const DISPOSITIONS = [
	'1+kk', '1+1', '2+kk', '2+1', '3+kk', '3+1', '4+kk', '4+1', '5+kk', '5+1',
	'6+kk', '6+1', '7+kk', '7+1', '8+kk', '8+1', '9+kk', '9+1', 'atypicky'
] as const;

const KIND_LABEL: Record<string, string> = {
	kraj: 'kraj', okres: 'okres', obec: 'obec', obvod: 'obvod',
	mestska_cast: 'městská část', cast_obce: 'část obce', ulice: 'ulice'
};

export type Draft = {
	name: string;
	paused: boolean;
	portals: Portal[];
	offerType: 'rent' | 'sale';
	estateType: 'flat' | 'house' | 'land' | 'cottage';
	place: NamedPlace | null;
	minPrice: number | null;
	maxPrice: number | null;
	minSize: number | null;
	minLand: number | null;
	minRooms: number | null;
	maxRooms: number | null;
	kitchen: 'kitchenette' | 'separate' | null;
	pricePerM2Weight: number;
	dispositionWeight: number;
	preferredDispositions: string[];
	sizeWeight: number;
	idealSize: number | null;
	placeWeight: number;
	preferredPlaces: NamedPlace[];
	landWeight: number;
	idealLand: number | null;
	priceWeight: number;
	maxGoodPrice: number | null;
};

export function placeLabel(place: NamedPlace): string {
	const context = [KIND_LABEL[place.kind] ?? place.kind, place.obec, place.okres].filter(Boolean);
	return `${place.name ?? `${place.kind} ${place.code}`} (${context.join(', ')})`;
}

export type PlaceSearch = (query: string, within: NamedPlace | null) => Promise<NamedPlace[]>;

export function weights(d: Draft): { label: string; weight: number }[] {
	return [
		{ label: 'Price per m²', weight: d.pricePerM2Weight },
		{ label: 'Layout', weight: d.dispositionWeight },
		{ label: 'Size', weight: d.sizeWeight },
		{ label: 'Place', weight: d.placeWeight },
		{ label: 'Land', weight: d.landWeight },
		{ label: 'Price', weight: d.priceWeight }
	];
}
