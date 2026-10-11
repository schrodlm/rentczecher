import type { PostingPricesModel } from '$lib/api/client';

/* The plot's size in its own units, and the margin kept clear inside it so
the line never runs along an edge. */
export type PlotBox = { width: number; height: number; marginX: number; marginY: number };

/* One posting's prices as a step line across the plot, ending at its current
price. */
export type PriceLine = {
	listingId: string;
	source: string;
	own: boolean;
	path: string;
	endX: number;
	endY: number;
	current: number;
};

/* Every posting's line on one shared scale, with the span it covers. */
export type PriceChart = {
	lines: PriceLine[];
	lowest: number;
	highest: number;
	since: string;
	until: string;
};

/* Null when no posting has a price yet. A price holds until the next one was
first seen. */
export function priceChartOf(
	postings: readonly PostingPricesModel[],
	ownListingId: string,
	box: PlotBox
): PriceChart | null {
	const priced = postings.filter((posting) => posting.changes.length > 0);
	if (priced.length === 0) return null;
	const changes = priced.flatMap((posting) => posting.changes);
	const prices = changes.map((change) => change.price);
	const lowest = Math.min(...prices);
	const highest = Math.max(...prices);
	const since = changes.map((change) => change.first_seen_at).reduce((a, b) => (a < b ? a : b));
	const until = changes.map((change) => change.last_seen_at).reduce((a, b) => (a > b ? a : b));
	const start = Date.parse(since);
	const end = Date.parse(until);

	const x = (at: string): number => {
		if (end === start) return box.width / 2;
		return box.marginX + ((Date.parse(at) - start) / (end - start)) * (box.width - 2 * box.marginX);
	};
	const y = (price: number): number => {
		if (highest === lowest) return box.height / 2;
		return box.marginY + ((highest - price) / (highest - lowest)) * (box.height - 2 * box.marginY);
	};

	const lines = priced.map((posting): PriceLine => {
		const steps = posting.changes.map((change, index) => {
			const next = posting.changes[index + 1];
			const heldUntil = next === undefined ? change.last_seen_at : next.first_seen_at;
			return `${index === 0 ? 'M' : 'L'}${x(change.first_seen_at)},${y(change.price)} L${x(heldUntil)},${y(change.price)}`;
		});
		const last = posting.changes[posting.changes.length - 1];
		return {
			listingId: posting.listing_id,
			source: posting.source,
			own: posting.listing_id === ownListingId,
			path: steps.join(' '),
			endX: x(last.last_seen_at),
			endY: y(last.price),
			current: last.price
		};
	});
	return { lines, lowest, highest, since, until };
}
