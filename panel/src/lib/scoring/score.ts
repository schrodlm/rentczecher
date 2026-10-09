import type { components } from '$lib/api/types.gen';

type ListingModel = components['schemas']['ListingModel'];
type LocationModel = components['schemas']['LocationModel'];
type PreferencesModel = components['schemas']['PreferencesModel'];
type PlaceRef = components['schemas']['PlaceRefModel'];

export type ScoredListing = Pick<ListingModel, 'price' | 'size_m2' | 'land_m2' | 'disposition' | 'resolved_location'>;
export type ScoringPreferences = Omit<PreferencesModel, 'preferred_places'> & { preferred_places: PlaceRef[] };

/* One preference's share of a score: the points it gives a listing out of
its weight. */
export type ScorePart = {
	preference: 'pricePerM2' | 'disposition' | 'size' | 'place' | 'land' | 'price';
	points: number;
	weight: number;
};

/* How well a listing meets a profile's preferences. Each preference with a
weight scores 0 to 100 and adds that share of its weight, so weights adding
up to 100 give a score out of 100. A preference whose listing fact is
missing adds nothing. */
export function scoreListing(listing: ScoredListing, preferences: ScoringPreferences): number {
	let total = 0;
	for (const part of scoreParts(listing, preferences)) total += part.points;
	return roundHalfToEven(total);
}

/* The points each preference gives a listing, in the order they add up. */
export function scoreParts(listing: ScoredListing, preferences: ScoringPreferences): ScorePart[] {
	const parts: ScorePart[] = [];

	if (preferences.price_per_m2_weight && listing.price !== null && listing.size_m2 && listing.size_m2 > 0) {
		const pricePerM2 = listing.price / listing.size_m2;
		const score = Math.max(0, Math.min(100, (550 - pricePerM2) / 2.5));
		parts.push(part('pricePerM2', score, preferences.price_per_m2_weight));
	}

	if (preferences.disposition_weight && listing.disposition !== null) {
		const preferredDispositions: readonly string[] = preferences.preferred_dispositions;
		const rank = preferredDispositions.indexOf(listing.disposition);
		const score = rank === -1 ? 10 : Math.max(20, 100 - rank * 20);
		parts.push(part('disposition', score, preferences.disposition_weight));
	}

	if (preferences.size_weight && listing.size_m2 && preferences.ideal_size_m2) {
		const score = Math.min(100, (listing.size_m2 / preferences.ideal_size_m2) * 100);
		parts.push(part('size', score, preferences.size_weight));
	}

	if (preferences.place_weight) {
		const location = listing.resolved_location;
		let score = 20;
		if (location !== null) {
			const rank = preferences.preferred_places.findIndex((place) => liesIn(location, place));
			if (rank !== -1) score = Math.max(20, 100 - rank * 20);
		}
		parts.push(part('place', score, preferences.place_weight));
	}

	if (preferences.land_weight && listing.land_m2 && preferences.ideal_land_m2) {
		const score = Math.min(100, (listing.land_m2 / preferences.ideal_land_m2) * 100);
		parts.push(part('land', score, preferences.land_weight));
	}

	if (preferences.price_weight && listing.price && preferences.max_good_price) {
		// Full points up to the good price, none from twice it.
		const ratio = listing.price / preferences.max_good_price;
		const score = Math.max(0, Math.min(100, (2 - ratio) * 100));
		parts.push(part('price', score, preferences.price_weight));
	}

	return parts;
}

function part(preference: ScorePart['preference'], score: number, weight: number): ScorePart {
	return { preference, points: (score * weight) / 100, weight };
}

function liesIn(location: LocationModel, place: PlaceRef): boolean {
	const unit = {
		kraj: location.kraj,
		okres: location.okres,
		obec: location.obec,
		obvod: location.obvod,
		mestska_cast: location.mestska_cast,
		cast_obce: location.cast_obce,
		ulice: location.ulice
	}[place.kind];
	return unit !== null && unit.code === place.code;
}

/* Halves go to the even neighbour, where Math.round would send them up. */
function roundHalfToEven(value: number): number {
	const floor = Math.floor(value);
	const fraction = value - floor;
	if (fraction > 0.5) return floor + 1;
	if (fraction < 0.5) return floor;
	return floor % 2 === 0 ? floor : floor + 1;
}
