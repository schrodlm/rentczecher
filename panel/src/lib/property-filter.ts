import type { TrackedPropertyModel } from '$lib/api/client';
import { Scale } from '$lib/forms/scale';
import { LAYOUTS, type Layout } from '$lib/layouts';
import { PORTALS, type Portal } from '$lib/portals';

/* Which of a profile's listings the inbox shows for now, without changing
the profile. An empty list of portals or layouts and a missing bound each
let every listing through. */
export type PropertyFilter = {
	portals: Portal[];
	onlyPriceDrops: boolean;
	minimumScore: number | null;
	layouts: Layout[];
	minPrice: number | null;
	maxPrice: number | null;
	minSize: number | null;
	maxSize: number | null;
	minLand: number | null;
	maxLand: number | null;
};

/* One part of the filter, as its chip names and clears it. */
export type Facet = 'portals' | 'priceDrops' | 'score' | 'layouts' | 'price' | 'size' | 'land';

export function noFilter(): PropertyFilter {
	return {
		portals: [],
		onlyPriceDrops: false,
		minimumScore: null,
		layouts: [],
		minPrice: null,
		maxPrice: null,
		minSize: null,
		maxSize: null,
		minLand: null,
		maxLand: null
	};
}

export function activeFacets(filter: PropertyFilter): Facet[] {
	const facets: Facet[] = [];
	if (filter.portals.length > 0) facets.push('portals');
	if (filter.onlyPriceDrops) facets.push('priceDrops');
	if (filter.minimumScore !== null) facets.push('score');
	if (filter.layouts.length > 0) facets.push('layouts');
	if (filter.minPrice !== null || filter.maxPrice !== null) facets.push('price');
	if (filter.minSize !== null || filter.maxSize !== null) facets.push('size');
	if (filter.minLand !== null || filter.maxLand !== null) facets.push('land');
	return facets;
}

export function withoutFacet(filter: PropertyFilter, facet: Facet): PropertyFilter {
	if (facet === 'portals') return { ...filter, portals: [] };
	if (facet === 'priceDrops') return { ...filter, onlyPriceDrops: false };
	if (facet === 'score') return { ...filter, minimumScore: null };
	if (facet === 'layouts') return { ...filter, layouts: [] };
	if (facet === 'price') return { ...filter, minPrice: null, maxPrice: null };
	if (facet === 'size') return { ...filter, minSize: null, maxSize: null };
	return { ...filter, minLand: null, maxLand: null };
}

/* A listing lacking a fact a facet asks about does not pass that facet. */
export function passes(listing: TrackedPropertyModel, filter: PropertyFilter, score: number | null): boolean {
	if (filter.portals.length > 0 && !filter.portals.some((portal) => portal === listing.source)) return false;
	if (filter.onlyPriceDrops && listing.price_drop_from === null) return false;
	if (filter.minimumScore !== null && (score === null || score < filter.minimumScore)) return false;
	if (filter.layouts.length > 0 && !filter.layouts.some((layout) => layout === listing.disposition)) return false;
	if (!within(listing.price, filter.minPrice, filter.maxPrice)) return false;
	if (!within(listing.size_m2, filter.minSize, filter.maxSize)) return false;
	return within(listing.land_m2, filter.minLand, filter.maxLand);
}

function within(value: number | null, low: number | null, high: number | null): boolean {
	if (low === null && high === null) return true;
	if (value === null) return false;
	return (low === null || value >= low) && (high === null || value <= high);
}

/* The portals and layouts some listing has, in the order the app lists them. */
export function portalsAmong(listings: readonly TrackedPropertyModel[]): Portal[] {
	return PORTALS.map((shown) => shown.portal).filter((portal) => listings.some((listing) => listing.source === portal));
}

export function layoutsAmong(listings: readonly TrackedPropertyModel[]): Layout[] {
	return LAYOUTS.filter((layout) => listings.some((listing) => listing.disposition === layout));
}

const SCALE_STOPS = 20;

/* A slider scale from the lowest to the highest value the listings have, in
round steps, or null when fewer than two listings differ in it. */
export function scaleAmong(
	listings: readonly TrackedPropertyModel[],
	factOf: (listing: TrackedPropertyModel) => number | null,
	roundTo: number
): Scale | null {
	const values = listings.map(factOf).filter((value) => value !== null);
	if (values.length === 0) return null;
	const lowest = Math.floor(Math.min(...values) / roundTo) * roundTo;
	const highest = Math.ceil(Math.max(...values) / roundTo) * roundTo;
	if (highest === lowest) return null;
	const step = Math.max(roundTo, Math.ceil((highest - lowest) / SCALE_STOPS / roundTo) * roundTo);
	const stops: number[] = [];
	for (let stop = lowest; stop < highest; stop += step) stops.push(stop);
	stops.push(highest);
	return new Scale(stops);
}
