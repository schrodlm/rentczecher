import type { NamedPlace } from '$lib/api/client';
import type { components } from '$lib/api/types.gen';
import { LAYOUTS, type Layout } from '$lib/layouts';
import { preferencesBody, type PreferredValues, type Weights } from './preferences';
import { scoreListing, scoreParts, type ScorePart } from './score';

type CriteriaBody = components['schemas']['CriteriaBody'];
type LocationModel = components['schemas']['LocationModel'];

/* The search an example has to fit, and what it is scored against. */
export type ExampleProfile = {
	criteria: Omit<CriteriaBody, 'place'>;
	searchPlace: NamedPlace | null;
	preferredValues: PreferredValues;
	weights: Weights;
};

/* A made-up listing the search would show, and how it scores. */
export type ExampleListing = {
	target: number;
	price: number;
	size: number | null;
	land: number | null;
	layout: Layout | null;
	layoutPreferred: boolean;
	place: NamedPlace | null;
	placePreferred: boolean;
	score: number;
	parts: ScorePart[];
	// False when no listing the search allows scores near the target.
	nearTarget: boolean;
};

const TARGETS = [100, 50, 10];
const NEAR = 5;
const SAMPLES = 100;
// Below this step along the way the listing is on neither preferred list.
const OFF_THE_LISTS = 0.2;
// Stand-ins for a preferred value not yet chosen, so a preference still has a
// scale.
const FALLBACK_PREFERRED_FLAT_M2 = 60;
const FALLBACK_PREFERRED_HOUSE_M2 = 120;
const FALLBACK_PREFERRED_LAND_M2 = 800;
const FALLBACK_PREFERRED_RENT = 20000;
const FALLBACK_PREFERRED_SALE_PRICE = 5_000_000;

/* Three listings the search would show, scoring as near 100, 50 and 10 as
the profile allows. When its limits keep every listing alike, two targets
fall on one listing and only the lower one is kept. */
export function exampleListings(profile: ExampleProfile): ExampleListing[] {
	const preferences = preferencesBody(profile.preferredValues, profile.weights, profile.criteria.estate_type);
	const samples = Array.from({ length: SAMPLES + 1 }, (_unused, step) => {
		const example = exampleAt(profile, step / SAMPLES);
		const listing = scoredListing(example);
		return { ...example, score: scoreListing(listing, preferences), parts: scoreParts(listing, preferences) };
	});
	const picked = TARGETS.map((target) => {
		const nearest = samples.reduce((best, sample) =>
			Math.abs(sample.score - target) < Math.abs(best.score - target) ? sample : best
		);
		return { ...nearest, target, nearTarget: Math.abs(nearest.score - target) <= NEAR };
	});
	return picked.filter((card, index) => !picked.slice(index + 1).some((later) => later.score === card.score));
}

type Example = Omit<ExampleListing, 'target' | 'score' | 'parts' | 'nearTarget'>;

/* A listing that fits the search and gets better on every preference as along
runs from 0 to 1. */
function exampleAt(profile: ExampleProfile, along: number): Example {
	const { criteria, preferredValues } = profile;
	const fallbackSize = criteria.estate_type === 'flat' ? FALLBACK_PREFERRED_FLAT_M2 : FALLBACK_PREFERRED_HOUSE_M2;
	const preferredSize = preferredValues.preferred_size_m2 ?? fallbackSize;
	const preferredLand = preferredValues.preferred_land_m2 ?? FALLBACK_PREFERRED_LAND_M2;
	const fallbackPrice = criteria.offer_type === 'rent' ? FALLBACK_PREFERRED_RENT : FALLBACK_PREFERRED_SALE_PRICE;
	const preferredPrice = preferredValues.preferred_price ?? fallbackPrice;
	const priceStep = criteria.offer_type === 'rent' ? 500 : 50_000;

	const size =
		criteria.estate_type === 'land'
			? null
			: within(roundTo(between(0.3 * preferredSize, preferredSize, along), 1), criteria.min_size_m2, criteria.max_size_m2);
	const land =
		criteria.estate_type === 'flat'
			? null
			: within(roundTo(between(0.2 * preferredLand, preferredLand, along), 10), criteria.min_land_m2, null);
	const price = within(
		roundTo(between(2 * preferredPrice, 0.8 * preferredPrice, along), priceStep),
		criteria.min_price,
		criteria.max_price
	);

	const layouts = preferredValues.preferred_dispositions;
	const layoutPreferred = along >= OFF_THE_LISTS && layouts.length > 0 && criteria.estate_type !== 'land';
	const places = preferredValues.preferred_places;
	const placePreferred = along >= OFF_THE_LISTS && places.length > 0;

	return {
		price,
		size,
		land,
		layout: criteria.estate_type === 'land' ? null : layoutPreferred ? layouts[0] : layoutOffTheList(profile),
		layoutPreferred,
		place: placePreferred ? places[0] : profile.searchPlace,
		placePreferred
	};
}

/* A layout the search accepts that is not among the preferred ones. */
function layoutOffTheList(profile: ExampleProfile): Layout {
	const preferred: readonly Layout[] = profile.preferredValues.preferred_dispositions;
	const accepted = profile.criteria.dispositions.length > 0 ? profile.criteria.dispositions : LAYOUTS;
	return accepted.find((layout) => !preferred.includes(layout)) ?? accepted[0];
}

function scoredListing(example: Example) {
	return {
		price: example.price,
		size_m2: example.size,
		land_m2: example.land,
		disposition: example.layout,
		resolved_location: example.placePreferred && example.place !== null ? locationIn(example.place) : null
	};
}

/* A location that lies in the place, which is all the place preference
reads of it. */
function locationIn(place: NamedPlace): LocationModel {
	const unit = { code: place.code, name: place.name ?? '' };
	return {
		kraj: place.kind === 'kraj' ? unit : { code: 0, name: '' },
		okres: place.kind === 'okres' ? unit : null,
		obec: place.kind === 'obec' ? unit : null,
		obvod: place.kind === 'obvod' ? unit : null,
		mestska_cast: place.kind === 'mestska_cast' ? unit : null,
		cast_obce: place.kind === 'cast_obce' ? unit : null,
		ulice: place.kind === 'ulice' ? unit : null,
		cislo_popisne: null,
		cislo_orientacni: null
	};
}

function between(from: number, to: number, along: number): number {
	return from + (to - from) * along;
}

function roundTo(value: number, step: number): number {
	return Math.max(step, Math.round(value / step) * step);
}

function within(value: number, low: number | null, high: number | null): number {
	return Math.min(high ?? Infinity, Math.max(low ?? -Infinity, value));
}
