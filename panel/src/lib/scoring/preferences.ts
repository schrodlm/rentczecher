import type { NamedPlace } from '$lib/api/client';
import type { components } from '$lib/api/types.gen';
import type { Layout } from '$lib/layouts';
import { settled } from './split';

type EstateType = components['schemas']['CriteriaBody']['estate_type'];
type PreferencesBody = components['schemas']['PreferencesBody'];

/* What each preference scores against, without how much it matters. */
export type PreferredValues = {
	preferred_price: number | null;
	preferred_size_m2: number | null;
	preferred_land_m2: number | null;
	preferred_dispositions: Layout[];
	preferred_places: NamedPlace[];
};

/* A preference the editor offers. Price per m² is left out until its fixed
scale fits more than Praha rents. */
export type Preference = 'price' | 'size' | 'land' | 'layout' | 'place';
export const PREFERENCES: readonly Preference[] = ['price', 'size', 'land', 'layout', 'place'];

export type Weights = Record<Preference, number>;

/* The preferences that fit a type of estate: land has no size or layout, and a
flat has no land. */
export function preferencesFor(estateType: EstateType): Preference[] {
	if (estateType === 'flat') return ['price', 'size', 'layout', 'place'];
	if (estateType === 'land') return ['price', 'land', 'place'];
	return [...PREFERENCES];
}

/* Whether a preference has the preferred value it scores against, without
which it cannot count. */
export function isReady(preference: Preference, values: PreferredValues): boolean {
	if (preference === 'price') return values.preferred_price !== null;
	if (preference === 'size') return values.preferred_size_m2 !== null;
	if (preference === 'land') return values.preferred_land_m2 !== null;
	if (preference === 'layout') return values.preferred_dispositions.length > 0;
	return values.preferred_places.length > 0;
}

/* The preferences that count towards the score: those that fit the estate
and have their preferred value. */
export function countingFor(values: PreferredValues, estateType: EstateType): Preference[] {
	return preferencesFor(estateType).filter((preference) => isReady(preference, values));
}

/* The weights a profile stores: the counting preferences' weights grown to add
up to 100, every other preference at 0. */
export function storedWeights(values: PreferredValues, weights: Weights, estateType: EstateType): Weights {
	return settled(weights, countingFor(values, estateType));
}

/* The preferences a profile stores: each one's preferred value and its
stored weight. */
export function preferencesBody(values: PreferredValues, weights: Weights, estateType: EstateType): PreferencesBody {
	const stored = storedWeights(values, weights, estateType);
	return {
		price_per_m2_weight: 0,
		disposition_weight: stored.layout,
		preferred_dispositions: [...values.preferred_dispositions],
		size_weight: stored.size,
		preferred_size_m2: values.preferred_size_m2,
		place_weight: stored.place,
		preferred_places: values.preferred_places.map((place) => ({ kind: place.kind, code: place.code })),
		land_weight: stored.land,
		preferred_land_m2: values.preferred_land_m2,
		price_weight: stored.price,
		preferred_price: values.preferred_price
	};
}
