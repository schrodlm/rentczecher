import type { ListingModel } from '$lib/api/client';

export function listing(id: string, overrides: Partial<ListingModel> = {}): ListingModel {
	return {
		id,
		source: 'sreality',
		url: `https://sreality.cz/detail/${id}`,
		title: 'Byt 2+kk',
		location: 'Praha 7',
		size_m2: 52,
		disposition: '2+kk',
		first_seen_at: new Date().toISOString(),
		viewed_at: null,
		favourited_at: null,
		price: 21000,
		price_drop_from: null,
		sibling_sources: [],
		...overrides
	};
}
