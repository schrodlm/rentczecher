import type { PostingPricesModel, TrackedPropertyModel } from '$lib/api/client';
import type { components } from '$lib/api/types.gen';

type LocationModel = components['schemas']['LocationModel'];

/* Made-up flats the welcome wizard shows a profile at work on, real enough
to read like the inbox's own. */

export const PRAHA_7: LocationModel = {
	kraj: { code: 19, name: 'Hlavní město Praha' },
	okres: null,
	obec: { code: 554782, name: 'Praha' },
	obvod: { code: 78, name: 'Praha 7' },
	mestska_cast: { code: 500186, name: 'Praha 7' },
	cast_obce: null,
	ulice: null,
	cislo_popisne: null,
	cislo_orientacni: null
};

function sampleFlat(
	id: string,
	index: number,
	source: string,
	price: number,
	sizeM2: number,
	layout: string,
	place: string
): TrackedPropertyModel {
	return {
		id,
		index,
		listing_id: `${source}:${id}`,
		source,
		url: `https://example.invalid/${id}`,
		title: `Pronájem bytu ${layout} ${sizeM2} m²`,
		location_raw_text: place,
		resolved_location: PRAHA_7,
		point: null,
		size_m2: sizeM2,
		land_m2: null,
		disposition_raw_text: layout,
		disposition: layout,
		first_seen_at: '2026-09-01T08:00:00Z',
		viewed_at: null,
		favourited_at: null,
		updated_at: null,
		price,
		price_drop_from: null,
		sibling_sources: [],
		main_photo: null
	};
}

export const ONE_FLAT = sampleFlat('holesovice', 1, 'sreality', 22900, 58, '2+kk', 'Praha 7, Holešovice');

export const RANKED_FLATS: readonly { flat: TrackedPropertyModel; score: number }[] = [
	{ flat: ONE_FLAT, score: 87 },
	{ flat: sampleFlat('letna', 2, 'bezrealitky', 24500, 61, '3+kk', 'Praha 7, Letná'), score: 62 },
	{ flat: sampleFlat('troja', 3, 'remax', 19800, 41, '2+kk', 'Praha 7, Troja'), score: 35 }
];

const day = (offset: number) => new Date(Date.UTC(2026, 8, 1 + offset, 8)).toISOString();

export const PRICE_HISTORY: readonly PostingPricesModel[] = [
	{
		listing_id: ONE_FLAT.listing_id,
		source: ONE_FLAT.source,
		url: ONE_FLAT.url,
		changes: [
			{ price: 24500, charges: null, first_seen_at: day(0), last_seen_at: day(9) },
			{ price: 23500, charges: null, first_seen_at: day(10), last_seen_at: day(19) },
			{ price: 22900, charges: null, first_seen_at: day(20), last_seen_at: day(30) }
		]
	},
	{
		listing_id: 'bezrealitky:holesovice',
		source: 'bezrealitky',
		url: 'https://example.invalid/holesovice',
		changes: [{ price: 23900, charges: null, first_seen_at: day(6), last_seen_at: day(30) }]
	}
];
