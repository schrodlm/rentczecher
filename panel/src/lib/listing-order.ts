import type { ListingModel } from '$lib/api/client';

/* What a profile's listings can be ordered by. */
export type SortField = 'score' | 'date' | 'price' | 'pricePerM2' | 'size';

export const SORT_FIELDS: readonly SortField[] = ['score', 'date', 'price', 'pricePerM2', 'size'];

/* A field to order by and which way. */
export type ListingOrder = { field: SortField; descending: boolean };

/* The way a field is first ordered when picked: the best score, the newest,
the largest, the cheapest. */
export function naturalOrder(field: SortField): ListingOrder {
	return { field, descending: field === 'score' || field === 'date' || field === 'size' };
}

/* The listings in an order. A listing missing the field goes last either way,
and ties go newest first. The date is the section's own, given by `dateOf`. */
export function sortListings(
	listings: readonly ListingModel[],
	order: ListingOrder,
	scoreOf: (listing: ListingModel) => number | null,
	dateOf: (listing: ListingModel) => string
): ListingModel[] {
	const newestFirst = (a: ListingModel, b: ListingModel) => dateOf(b).localeCompare(dateOf(a));
	if (order.field === 'date') {
		const sorted = [...listings].sort(newestFirst);
		return order.descending ? sorted : sorted.reverse();
	}
	const valueOf = (listing: ListingModel): number | null => {
		if (order.field === 'score') return scoreOf(listing);
		if (order.field === 'price') return listing.price;
		if (order.field === 'pricePerM2') return pricePerM2(listing);
		return listing.size_m2;
	};
	return [...listings].sort((a, b) => {
		const valueA = valueOf(a);
		const valueB = valueOf(b);
		if (valueA === null && valueB === null) return newestFirst(a, b);
		if (valueA === null) return 1;
		if (valueB === null) return -1;
		if (valueA === valueB) return newestFirst(a, b);
		return order.descending ? valueB - valueA : valueA - valueB;
	});
}

function pricePerM2(listing: ListingModel): number | null {
	if (listing.price === null || listing.size_m2 === null || listing.size_m2 <= 0) return null;
	return listing.price / listing.size_m2;
}
