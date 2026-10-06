/* PROTOTYPE, throwaway. The editable shape of a profile shared by the editor
variants, and the request each would send. Nothing here is wired to a real
mutation: the host only shows the request. */

import type { components } from '$lib/api/types.gen';
import type { ProfileModel } from '$lib/api/client';
import { weights as wishWeights, type Wish } from './scoring';

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

export const KIND_LABEL: Record<string, string> = {
	kraj: 'kraj',
	okres: 'okres',
	obec: 'obec',
	obvod: 'obvod',
	mestska_cast: 'městská část',
	cast_obce: 'část obce',
	ulice: 'ulice'
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
	maxSize: number | null;
	minLand: number | null;
	layouts: string[];
	importance: Record<Wish, number>;
	preferredDispositions: string[];
	idealSize: number | null;
	preferredPlaces: NamedPlace[];
	idealLand: number | null;
	maxGoodPrice: number | null;
};

const NO_IMPORTANCE: Record<Wish, number> = { price: 0, pricePerM2: 0, size: 0, land: 0, layout: 0, place: 0 };

/* The importance step closest to a stored weight's share. */
function importanceOf(weight: number, total: number): number {
	if (weight <= 0 || total <= 0) return 0;
	const share = weight / total;
	return share > 0.4 ? 4 : share > 0.25 ? 3 : share > 0.12 ? 2 : 1;
}

export function emptyDraft(): Draft {
	return {
		name: '',
		paused: false,
		portals: [...PORTALS],
		offerType: 'rent',
		estateType: 'flat',
		place: null,
		minPrice: null,
		maxPrice: null,
		minSize: null,
		maxSize: null,
		minLand: null,
		layouts: [],
		importance: { ...NO_IMPORTANCE },
		preferredDispositions: [],
		idealSize: null,
		preferredPlaces: [],
		idealLand: null,
		maxGoodPrice: null
	};
}

export function draftFromProfile(profile: ProfileModel): Draft {
	const c = profile.criteria;
	const p = profile.preferences;
	const total = p.price_per_m2_weight + p.disposition_weight + p.size_weight + p.place_weight + p.land_weight + p.price_weight;
	return {
		name: profile.name,
		paused: profile.paused_at !== null,
		portals: [...profile.portals],
		offerType: c.offer_type,
		estateType: c.estate_type,
		place: c.place,
		minPrice: c.min_price,
		maxPrice: c.max_price,
		minSize: c.min_size_m2,
		maxSize: null,
		minLand: c.min_land_m2,
		layouts: [],
		importance: {
			price: importanceOf(p.price_weight, total),
			pricePerM2: importanceOf(p.price_per_m2_weight, total),
			size: importanceOf(p.size_weight, total),
			land: importanceOf(p.land_weight, total),
			layout: importanceOf(p.disposition_weight, total),
			place: importanceOf(p.place_weight, total)
		},
		preferredDispositions: [...p.preferred_dispositions],
		idealSize: p.ideal_size_m2,
		preferredPlaces: [...p.preferred_places],
		idealLand: p.ideal_land_m2,
		maxGoodPrice: p.max_good_price
	};
}

function placeRef(place: NamedPlace) {
	return { kind: place.kind, code: place.code };
}

function preferencesBody(d: Draft) {
	const w = wishWeights(d);
	return {
		price_per_m2_weight: w.pricePerM2,
		disposition_weight: w.layout,
		preferred_dispositions: w.layout ? d.preferredDispositions : [],
		size_weight: w.size,
		ideal_size_m2: d.idealSize,
		place_weight: w.place,
		preferred_places: w.place ? d.preferredPlaces.map(placeRef) : [],
		land_weight: w.land,
		ideal_land_m2: d.idealLand,
		price_weight: w.price,
		max_good_price: d.maxGoodPrice
	};
}

export function request(d: Draft, profileId: string | null) {
	if (profileId !== null) {
		return {
			method: 'PUT',
			path: `/v1/profiles/${profileId}`,
			body: { name: d.name, paused: d.paused, portals: d.portals, preferences: preferencesBody(d) }
		};
	}
	return {
		method: 'POST',
		path: '/v1/profiles',
		body: {
			name: d.name,
			portals: d.portals,
			// Proposed shape: a maximum size and a set of layouts are not in
			// the API yet.
			criteria: {
				offer_type: d.offerType,
				estate_type: d.estateType,
				place: d.place ? placeRef(d.place) : null,
				min_price: d.minPrice,
				max_price: d.maxPrice,
				min_size_m2: d.minSize,
				max_size_m2: d.maxSize,
				min_land_m2: d.minLand,
				layouts: d.layouts
			},
			preferences: preferencesBody(d)
		}
	};
}

export function placeLabel(place: NamedPlace): string {
	const context = [KIND_LABEL[place.kind] ?? place.kind, place.obec, place.okres].filter(Boolean);
	return `${place.name ?? `${place.kind} ${place.code}`} (${context.join(', ')})`;
}

export type PlaceSearch = (query: string, within: NamedPlace | null, kinds?: string[]) => Promise<NamedPlace[]>;

export const KINDS_COARSEST_FIRST = ['kraj', 'okres', 'obec', 'obvod', 'mestska_cast', 'cast_obce', 'ulice'];
