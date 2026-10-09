import type { NamedPlace } from '$lib/api/client';
import type { components } from '$lib/api/types.gen';
import type { Layout } from '$lib/layouts';
import { settled } from './split';

type EstateType = components['schemas']['CriteriaBody']['estate_type'];
type PreferencesBody = components['schemas']['PreferencesBody'];

/* What each wish scores against, without how much it matters. */
export type WishSettings = {
	preferred_price: number | null;
	preferred_size_m2: number | null;
	preferred_land_m2: number | null;
	preferred_dispositions: Layout[];
	preferred_places: NamedPlace[];
};

/* A wish the editor offers. Price per m² is left out until its fixed scale
fits more than Praha rents. */
export type Wish = 'price' | 'size' | 'land' | 'layout' | 'place';
export const WISHES: readonly Wish[] = ['price', 'size', 'land', 'layout', 'place'];

export type Weights = Record<Wish, number>;

/* The wishes that fit a type of estate: land has no size or layout, and a
flat has no land. */
export function wishesFor(estateType: EstateType): Wish[] {
	if (estateType === 'flat') return ['price', 'size', 'layout', 'place'];
	if (estateType === 'land') return ['price', 'land', 'place'];
	return [...WISHES];
}

/* Whether a wish has the setting it scores against, without which it cannot
count. */
export function isReady(wish: Wish, settings: WishSettings): boolean {
	if (wish === 'price') return settings.preferred_price !== null;
	if (wish === 'size') return settings.preferred_size_m2 !== null;
	if (wish === 'land') return settings.preferred_land_m2 !== null;
	if (wish === 'layout') return settings.preferred_dispositions.length > 0;
	return settings.preferred_places.length > 0;
}

/* The wishes that count towards the score: those that fit the estate, have
their setting and are switched on. */
export function countingFor(settings: WishSettings, weights: Weights, estateType: EstateType): Wish[] {
	return wishesFor(estateType).filter((wish) => isReady(wish, settings) && weights[wish] > 0);
}

/* The weights a profile stores: the counting wishes' weights grown to add
up to 100, every other wish at 0. */
export function storedWeights(settings: WishSettings, weights: Weights, estateType: EstateType): Weights {
	return settled(weights, countingFor(settings, weights, estateType));
}

/* The preferences a profile stores: each wish's setting and its stored
weight. */
export function preferencesFor(settings: WishSettings, weights: Weights, estateType: EstateType): PreferencesBody {
	const stored = storedWeights(settings, weights, estateType);
	return {
		price_per_m2_weight: 0,
		disposition_weight: stored.layout,
		preferred_dispositions: [...settings.preferred_dispositions],
		size_weight: stored.size,
		preferred_size_m2: settings.preferred_size_m2,
		place_weight: stored.place,
		preferred_places: settings.preferred_places.map((place) => ({ kind: place.kind, code: place.code })),
		land_weight: stored.land,
		preferred_land_m2: settings.preferred_land_m2,
		price_weight: stored.price,
		preferred_price: settings.preferred_price
	};
}
