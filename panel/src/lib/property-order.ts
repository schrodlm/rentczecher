import type { TrackedPropertyModel } from '$lib/api/client';
import { pricePerM2 } from '$lib/property-detail';

/* What a profile's listings can be ordered by. */
export type SortField = 'score' | 'date' | 'price' | 'pricePerM2' | 'size';

export const SORT_FIELDS: readonly SortField[] = ['score', 'date', 'price', 'pricePerM2', 'size'];

/* A field to order by and which way. */
export type PropertyOrder = { field: SortField; descending: boolean };

/* The way a field is first ordered when picked: the best score, the newest,
the largest, the cheapest. */
export function naturalOrder(field: SortField): PropertyOrder {
	return { field, descending: field === 'score' || field === 'date' || field === 'size' };
}

/* The listings in an order. A listing missing the field goes last either way,
and ties go newest first. The date is the section's own, given by `dateOf`. */
export function sortProperties(
	listings: readonly TrackedPropertyModel[],
	order: PropertyOrder,
	scoreOf: (listing: TrackedPropertyModel) => number | null,
	dateOf: (listing: TrackedPropertyModel) => string
): TrackedPropertyModel[] {
	const newestFirst = (a: TrackedPropertyModel, b: TrackedPropertyModel) => dateOf(b).localeCompare(dateOf(a));
	if (order.field === 'date') {
		const sorted = [...listings].sort(newestFirst);
		return order.descending ? sorted : sorted.reverse();
	}
	const valueOf = (listing: TrackedPropertyModel): number | null => {
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
