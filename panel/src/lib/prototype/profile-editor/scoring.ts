/* PROTOTYPE, throwaway. A port of the engine's scoring formula, and three
synthetic listings that land near 100, 50 and 10 under a draft's wishes. */

import type { Draft, NamedPlace } from './draft.svelte';

export type Wish = 'price' | 'pricePerM2' | 'size' | 'land' | 'layout' | 'place';

export const IMPORTANCE = ['Off', 'Low', 'Medium', 'High', 'Top'] as const;
const IMPORTANCE_WEIGHT = [0, 1, 2, 3, 5];

export type Example = {
	size: number | null;
	land: number | null;
	price: number;
	layout: string | null;
	layoutRank: number | null;
	place: string;
	placeRank: number | null;
};

export type Part = { wish: Wish; label: string; fact: string; points: number; max: number };

/* The wishes that make sense for the draft's estate and offer type. */
export function visibleWishes(d: Draft): Wish[] {
	// Price per m² stays out of the editor until its fixed scale is settled.
	const wishes: Wish[] = ['price'];
	if (d.estateType !== 'land') wishes.push('size');
	if (d.estateType !== 'flat') wishes.push('land');
	if (d.estateType !== 'land') wishes.push('layout');
	wishes.push('place');
	return wishes;
}

/* A wish counts once it is visible, has importance and has its setting. */
export function ready(d: Draft, wish: Wish): boolean {
	if (wish === 'price') return d.maxGoodPrice !== null;
	if (wish === 'size') return d.idealSize !== null;
	if (wish === 'land') return d.idealLand !== null;
	if (wish === 'layout') return d.preferredDispositions.length > 0;
	if (wish === 'place') return d.preferredPlaces.length > 0;
	return true;
}

/* Weights that add up to 100, split by importance, by largest remainder. */
export function weights(d: Draft): Record<Wish, number> {
	const visible = visibleWishes(d);
	const raw = (Object.keys(d.importance) as Wish[]).map((wish) => ({
		wish,
		raw: visible.includes(wish) && ready(d, wish) ? IMPORTANCE_WEIGHT[d.importance[wish]] : 0
	}));
	const total = raw.reduce((sum, r) => sum + r.raw, 0);
	const result = { price: 0, pricePerM2: 0, size: 0, land: 0, layout: 0, place: 0 } as Record<Wish, number>;
	if (total === 0) return result;
	const exact = raw.map((r) => ({ ...r, exact: (100 * r.raw) / total }));
	exact.forEach((r) => (result[r.wish] = Math.floor(r.exact)));
	let left = 100 - exact.reduce((sum, r) => sum + Math.floor(r.exact), 0);
	[...exact].sort((a, b) => (b.exact % 1) - (a.exact % 1)).forEach((r) => {
		if (left > 0 && r.raw > 0) {
			result[r.wish] += 1;
			left -= 1;
		}
	});
	return result;
}

export function score(d: Draft, listing: Example): { total: number; parts: Part[] } {
	const w = weights(d);
	const parts: Part[] = [];
	if (w.pricePerM2 && listing.size) {
		const perM2 = listing.price / listing.size;
		const s = Math.max(0, Math.min(100, (550 - perM2) / 2.5));
		parts.push({ wish: 'pricePerM2', label: 'Price per m²', fact: `${Math.round(perM2)} Kč/m²`, points: (s * w.pricePerM2) / 100, max: w.pricePerM2 });
	}
	if (w.layout && listing.layout) {
		const s = listing.layoutRank === null ? 10 : Math.max(20, 100 - listing.layoutRank * 20);
		const fact = listing.layoutRank === null ? `${listing.layout}, not on your list` : `${listing.layout}, choice ${listing.layoutRank + 1}`;
		parts.push({ wish: 'layout', label: 'Layout', fact, points: (s * w.layout) / 100, max: w.layout });
	}
	if (w.size && listing.size && d.idealSize) {
		const s = Math.min(100, (listing.size / d.idealSize) * 100);
		parts.push({ wish: 'size', label: 'Size', fact: `${listing.size} m²`, points: (s * w.size) / 100, max: w.size });
	}
	if (w.place) {
		const s = listing.placeRank === null ? 20 : Math.max(20, 100 - listing.placeRank * 20);
		const fact = listing.placeRank === null ? `${listing.place}, not on your list` : `${listing.place}, choice ${listing.placeRank + 1}`;
		parts.push({ wish: 'place', label: 'Place', fact, points: (s * w.place) / 100, max: w.place });
	}
	if (w.land && listing.land && d.idealLand) {
		const s = Math.min(100, (listing.land / d.idealLand) * 100);
		parts.push({ wish: 'land', label: 'Land', fact: `${listing.land} m²`, points: (s * w.land) / 100, max: w.land });
	}
	if (w.price && d.maxGoodPrice) {
		const s = Math.max(0, Math.min(100, (2 - listing.price / d.maxGoodPrice) * 100));
		parts.push({ wish: 'price', label: 'Price', fact: `${listing.price.toLocaleString('cs-CZ')} Kč`, points: (s * w.price) / 100, max: w.price });
	}
	return { total: Math.round(parts.reduce((sum, p) => sum + p.points, 0)), parts };
}

const lerp = (a: number, b: number, q: number) => a + (b - a) * q;
const roundTo = (n: number, step: number) => Math.max(step, Math.round(n / step) * step);

function placeName(place: NamedPlace | undefined): string {
	return place?.name ?? 'somewhere else';
}

/* A listing that gets better on every wish as q runs from 0 to 1. */
function exampleAt(d: Draft, q: number): Example {
	const idealSize = d.idealSize ?? (d.estateType === 'flat' ? 60 : 120);
	const idealLand = d.idealLand ?? 800;
	// Examples are listings the search would show, so they keep its limits.
	const clamp = (n: number, low: number | null, high: number | null) => Math.min(high ?? Infinity, Math.max(low ?? -Infinity, n));
	const size = d.estateType === 'land' ? null : clamp(roundTo(lerp(0.3 * idealSize, idealSize, q), 1), d.minSize, d.maxSize);
	const land = d.estateType === 'flat' ? null : clamp(roundTo(lerp(0.2 * idealLand, idealLand, q), 10), d.minLand, null);
	const good = d.maxGoodPrice ?? (d.offerType === 'rent' ? 20000 : 5_000_000);
	let price = lerp(2 * good, 0.8 * good, q);
	if (!d.maxGoodPrice && size) price = lerp(560, 290, q) * size;
	price = clamp(roundTo(price, d.offerType === 'rent' ? 500 : 50_000), d.minPrice, d.maxPrice);

	const layouts = d.preferredDispositions;
	const layoutRank = q < 0.2 || layouts.length === 0 ? null : Math.round((1 - q) * (layouts.length - 1));
	const fallbackLayout = d.layouts.find((l) => !layouts.includes(l)) ?? (layouts.includes('1+1') ? '3+1' : '1+1');
	const places = d.preferredPlaces;
	const placeRank = q < 0.2 || places.length === 0 ? null : Math.round((1 - q) * (places.length - 1));
	return {
		size,
		land,
		price,
		layout: d.estateType === 'land' ? null : layoutRank === null ? fallbackLayout : layouts[layoutRank],
		layoutRank,
		place: placeRank === null ? placeName(d.place ?? undefined) : placeName(places[placeRank]),
		placeRank
	};
}

export type ExampleCard = { target: number; listing: Example; total: number; parts: Part[]; exact: boolean };

export function examples(d: Draft): ExampleCard[] {
	const samples = Array.from({ length: 101 }, (_, i) => {
		const listing = exampleAt(d, i / 100);
		return { listing, ...score(d, listing) };
	});
	const picked = [100, 50, 10].map((target) => {
		const best = samples.reduce((a, b) => (Math.abs(b.total - target) < Math.abs(a.total - target) ? b : a));
		return { target, ...best, exact: Math.abs(best.total - target) <= 5 };
	});
	// When the limits keep every listing high, two targets land on the same
	// listing, and only the lower one is kept.
	return picked.filter((card, i) => !picked.slice(i + 1).some((later) => later.total === card.total));
}
