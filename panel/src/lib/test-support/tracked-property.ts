import type { TrackedPropertyModel } from '$lib/api/client';

export function trackedProperty(id: string, overrides: Partial<TrackedPropertyModel> = {}): TrackedPropertyModel {
	return {
		id,
		index: 1,
		listing_id: id,
		source: 'sreality',
		url: `https://sreality.cz/detail/${id}`,
		title: 'Byt 2+kk',
		location_raw_text: 'Praha 7',
		resolved_location: null,
		point: null,
		size_m2: 52,
		land_m2: null,
		disposition_raw_text: '2+kk',
		disposition: '2+kk',
		first_seen_at: new Date().toISOString(),
		viewed_at: null,
		favourited_at: null,
		price: 21000,
		price_drop_from: null,
		sibling_sources: [],
		main_photo: null,
		...overrides
	};
}
