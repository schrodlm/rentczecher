import type { components } from '$lib/api/types.gen';

type EstateType = components['schemas']['CriteriaBody']['estate_type'];
type PreferencesBody = components['schemas']['PreferencesBody'];

/* What each wish scores against, without how much it matters. */
export type WishSettings = Pick<
	PreferencesBody,
	'max_good_price' | 'ideal_size_m2' | 'ideal_land_m2' | 'preferred_dispositions' | 'preferred_places'
>;

/* A wish the editor offers. Price per m² is left out until its fixed scale
fits more than Praha rents. */
export type Wish = 'price' | 'size' | 'land' | 'layout' | 'place';
export const WISHES: readonly Wish[] = ['price', 'size', 'land', 'layout', 'place'];

/* How much a wish matters, from off to top. */
export type Importance = 0 | 1 | 2 | 3 | 4;
export const IMPORTANCES: readonly Importance[] = [0, 1, 2, 3, 4];
export type Importances = Record<Wish, Importance>;
export type Weights = Record<Wish, number>;

// Each step's share of the score against the others, so top counts five
// times low.
const SHARE: Record<Importance, number> = { 0: 0, 1: 1, 2: 2, 3: 3, 4: 5 };
const NO_WEIGHTS: Weights = { price: 0, size: 0, land: 0, layout: 0, place: 0 };

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
	if (wish === 'price') return settings.max_good_price !== null;
	if (wish === 'size') return settings.ideal_size_m2 !== null;
	if (wish === 'land') return settings.ideal_land_m2 !== null;
	if (wish === 'layout') return settings.preferred_dispositions.length > 0;
	return settings.preferred_places.length > 0;
}

/* The preferences a profile stores: each wish's setting, and a weight for
each wish that fits the estate and has its setting. */
export function preferencesFor(settings: WishSettings, importances: Importances, estateType: EstateType): PreferencesBody {
	const counting = wishesFor(estateType).filter((wish) => isReady(wish, settings));
	const weights = weightsFor(importances, counting);
	return {
		price_per_m2_weight: 0,
		disposition_weight: weights.layout,
		preferred_dispositions: [...settings.preferred_dispositions],
		size_weight: weights.size,
		ideal_size_m2: settings.ideal_size_m2,
		place_weight: weights.place,
		preferred_places: settings.preferred_places.map((place) => ({ kind: place.kind, code: place.code })),
		land_weight: weights.land,
		ideal_land_m2: settings.ideal_land_m2,
		price_weight: weights.price,
		max_good_price: settings.max_good_price
	};
}

/* Weights adding up to 100, split between the counting wishes by their
importance. Rounding leftovers go to the largest remainders, ties to the
earlier wish, so the same importances always give the same weights. */
export function weightsFor(importances: Importances, counting: readonly Wish[]): Weights {
	const shares = WISHES.map((wish) => (counting.includes(wish) ? SHARE[importances[wish]] : 0));
	const total = shares.reduce((sum, share) => sum + share, 0);
	if (total === 0) return { ...NO_WEIGHTS };
	const exact = shares.map((share) => (100 * share) / total);
	const whole = exact.map(Math.floor);
	let left = 100 - whole.reduce((sum, weight) => sum + weight, 0);
	const byRemainder = WISHES.map((_wish, index) => index).sort(
		(a, b) => exact[b] - whole[b] - (exact[a] - whole[a])
	);
	for (const index of byRemainder) {
		if (left === 0) break;
		if (shares[index] === 0) continue;
		whole[index] += 1;
		left -= 1;
	}
	return {
		price: whole[0],
		size: whole[1],
		land: whole[2],
		layout: whole[3],
		place: whole[4]
	};
}

/* The importances whose weights come closest to stored ones. A profile
keeps only its weights, which hold how wishes compare, not how much: top
and top weigh the same as low and low. So among equal fits the highest
importances are read back. */
export function importancesFrom(weights: Weights): Importances {
	const weighted = WISHES.filter((wish) => weights[wish] > 0);
	let closest: Importances = { price: 0, size: 0, land: 0, layout: 0, place: 0 };
	let closestDistance = Infinity;
	let closestTotal = 0;
	for (const candidate of everyImportance(weighted)) {
		const candidateWeights = weightsFor(candidate, weighted);
		const distance = WISHES.reduce((sum, wish) => sum + Math.abs(candidateWeights[wish] - weights[wish]), 0);
		const total = WISHES.reduce((sum, wish) => sum + candidate[wish], 0);
		if (distance < closestDistance || (distance === closestDistance && total > closestTotal)) {
			closest = candidate;
			closestDistance = distance;
			closestTotal = total;
		}
	}
	return closest;
}

/* Every way of giving the weighted wishes an importance above off, the rest
off. */
function* everyImportance(weighted: Wish[]): Generator<Importances> {
	const levels = IMPORTANCES.filter((importance) => importance > 0);
	const choice = weighted.map(() => 0);
	while (true) {
		const importances: Importances = { price: 0, size: 0, land: 0, layout: 0, place: 0 };
		weighted.forEach((wish, index) => (importances[wish] = levels[choice[index]]));
		yield importances;
		let position = weighted.length - 1;
		while (position >= 0 && choice[position] === levels.length - 1) {
			choice[position] = 0;
			position -= 1;
		}
		if (position < 0) return;
		choice[position] += 1;
	}
}
