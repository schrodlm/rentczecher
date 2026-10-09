import type { NamedPlace, NewProfileBody, ProfileModel, ProfileUpdateBody } from '$lib/api/client';
import type { components } from '$lib/api/types.gen';
import { PORTALS, type Portal } from '$lib/portals';
import { preferencesBody, type PreferredValues, type Weights } from '$lib/scoring/preferences';

type CriteriaBody = components['schemas']['CriteriaBody'];

/* A profile's search without its place, which the draft holds named. */
export type Search = Omit<CriteriaBody, 'place'>;

/* What a profile still needs before it can be saved. */
export type Missing = 'name' | 'place' | 'portals';

/* A bound the user typed past its other end. */
export type CrossedRange = 'price' | 'size';

/* The profile the editor changes, from a blank one or from a stored one. A
new profile's search can change, a stored one's is fixed. */
export class ProfileDraft {
	name = $state('');
	paused = $state(false);
	portals = $state<Portal[]>([]);
	search = $state<Search>({
		offer_type: 'rent',
		estate_type: 'flat',
		min_price: null,
		max_price: null,
		min_size_m2: null,
		max_size_m2: null,
		min_land_m2: null,
		dispositions: []
	});
	place = $state<NamedPlace | null>(null);
	preferredValues = $state<PreferredValues>({
		preferred_price: null,
		preferred_size_m2: null,
		preferred_land_m2: null,
		preferred_dispositions: [],
		preferred_places: []
	});
	weights = $state<Weights>({ price: 0, size: 0, land: 0, layout: 0, place: 0 });

	missing: Missing[] = $derived.by(() => {
		const missing: Missing[] = [];
		if (this.name.trim() === '') missing.push('name');
		if (this.place === null) missing.push('place');
		if (this.portals.length === 0) missing.push('portals');
		return missing;
	});

	crossedRanges: CrossedRange[] = $derived.by(() => {
		const crossed: CrossedRange[] = [];
		if (isCrossed(this.search.min_price, this.search.max_price)) crossed.push('price');
		const hasSize = this.search.estate_type !== 'land';
		if (hasSize && isCrossed(this.search.min_size_m2, this.search.max_size_m2)) crossed.push('size');
		return crossed;
	});

	canSave = $derived(this.missing.length === 0 && this.crossedRanges.length === 0);

	/* A new profile watching every portal. */
	static blank(): ProfileDraft {
		const draft = new ProfileDraft();
		draft.portals = PORTALS.map((shown) => shown.portal);
		return draft;
	}

	/* A stored profile as the editor shows it. Price per m², which the editor
	leaves out, is dropped and saved at 0. */
	static of(profile: ProfileModel): ProfileDraft {
		const draft = new ProfileDraft();
		const criteria = profile.criteria;
		const preferences = profile.preferences;
		draft.name = profile.name;
		draft.paused = profile.paused_at !== null;
		draft.portals = [...profile.portals];
		draft.search = {
			offer_type: criteria.offer_type,
			estate_type: criteria.estate_type,
			min_price: criteria.min_price,
			max_price: criteria.max_price,
			min_size_m2: criteria.min_size_m2,
			max_size_m2: criteria.max_size_m2,
			min_land_m2: criteria.min_land_m2,
			dispositions: [...criteria.dispositions]
		};
		draft.place = criteria.place;
		draft.preferredValues = {
			preferred_price: preferences.preferred_price,
			preferred_size_m2: preferences.preferred_size_m2,
			preferred_land_m2: preferences.preferred_land_m2,
			preferred_dispositions: [...preferences.preferred_dispositions],
			preferred_places: [...preferences.preferred_places]
		};
		draft.weights = {
			price: preferences.price_weight,
			size: preferences.size_weight,
			land: preferences.land_weight,
			layout: preferences.disposition_weight,
			place: preferences.place_weight
		};
		return draft;
	}

	/* Rent and sale prices sit on different scales, so switching between them
	clears every price the draft holds. */
	setOfferType(offerType: Search['offer_type']): void {
		if (offerType === this.search.offer_type) return;
		this.search = { ...this.search, offer_type: offerType, min_price: null, max_price: null };
		this.preferredValues = { ...this.preferredValues, preferred_price: null };
	}

	/* Preferred places lie inside the search place, so a new search place
	clears them. */
	setPlace(place: NamedPlace | null): void {
		this.place = place;
		this.preferredValues = { ...this.preferredValues, preferred_places: [] };
	}

	newProfileBody(): NewProfileBody {
		if (this.place === null) throw new Error('a new profile needs its search place');
		return {
			name: this.name.trim(),
			portals: [...this.portals],
			criteria: { ...this.searchToSave(), place: { kind: this.place.kind, code: this.place.code } },
			preferences: preferencesBody(this.preferredValues, this.weights, this.search.estate_type)
		};
	}

	updateBody(): ProfileUpdateBody {
		return {
			name: this.name.trim(),
			paused: this.paused,
			portals: [...this.portals],
			preferences: preferencesBody(this.preferredValues, this.weights, this.search.estate_type)
		};
	}

	// The draft keeps every bound while the estate type changes, so switching
	// back restores them, but only the bounds that fit the type are saved.
	private searchToSave(): Search {
		const search = this.search;
		const hasSize = search.estate_type !== 'land';
		const hasLand = search.estate_type !== 'flat';
		return {
			offer_type: search.offer_type,
			estate_type: search.estate_type,
			min_price: search.min_price,
			max_price: search.max_price,
			min_size_m2: hasSize ? search.min_size_m2 : null,
			max_size_m2: hasSize ? search.max_size_m2 : null,
			min_land_m2: hasLand ? search.min_land_m2 : null,
			dispositions: hasSize ? [...search.dispositions] : []
		};
	}
}

function isCrossed(low: number | null, high: number | null): boolean {
	return low !== null && high !== null && low > high;
}
