import type { TrackedPropertyModel, PostingPricesModel } from '$lib/api/client';
import type { Translator } from '$lib/i18n/translator';

/* The listing's layout as shown, or null when the portal gave none. */
export function layoutOf(listing: TrackedPropertyModel, t: Translator): string | null {
	if (listing.disposition === 'atypicky') return t.t('atypical layout');
	return listing.disposition ?? listing.disposition_raw_text;
}

/* The listing's layout, size and place in one line, leaving out what it lacks. */
export function factsOf(listing: TrackedPropertyModel, t: Translator): string {
	return [layoutOf(listing, t), listing.size_m2 === null ? null : t.area(listing.size_m2), listing.location_raw_text]
		.filter((fact) => fact !== null)
		.join(' · ');
}

/* Where one fact of a listing, such as its price, sits among the same fact
of its profile's other listings. The lowest and highest take the listing in,
so it always lies between them, while the middle is the others' alone. */
export type Standing = {
	own: number;
	others: number[];
	lowest: number;
	highest: number;
	middle: number;
};

/* Null when the listing lacks the fact, or no other listing has it. */
export function standingOf(
	listing: TrackedPropertyModel,
	listings: readonly TrackedPropertyModel[],
	factOf: (listing: TrackedPropertyModel) => number | null
): Standing | null {
	const own = factOf(listing);
	if (own === null) return null;
	const others = listings
		.filter((other) => other.id !== listing.id)
		.map(factOf)
		.filter((value) => value !== null);
	if (others.length === 0) return null;
	const all = [own, ...others];
	return { own, others, lowest: Math.min(...all), highest: Math.max(...all), middle: median(others) };
}

/* Whether every other listing's value lies strictly above the listing's. */
export function isLowest(standing: Standing): boolean {
	return standing.others.every((value) => value > standing.own);
}

/* Whether every other listing's value lies strictly below the listing's. */
export function isHighest(standing: Standing): boolean {
	return standing.others.every((value) => value < standing.own);
}

/* How many of the other listings lie below the listing's value, in percent. */
export function percentBelow(standing: Standing): number {
	return Math.round((standing.others.filter((value) => value < standing.own).length / standing.others.length) * 100);
}

/* How many of the other listings lie above the listing's value, in percent. */
export function percentAbove(standing: Standing): number {
	return Math.round((standing.others.filter((value) => value > standing.own).length / standing.others.length) * 100);
}

/* How far the listing's value lies from the middle of the others, in
percent: below the middle when negative. */
export function percentFromMiddle(standing: Standing): number {
	return Math.round(((standing.own - standing.middle) / standing.middle) * 100);
}

/* Something that happened to a listing. */
export type PropertyEvent =
	| { kind: 'found'; at: string }
	| { kind: 'priceChange'; at: string; from: number; to: number }
	| { kind: 'viewed'; at: string }
	| { kind: 'favourite'; at: string };

/* What happened to a listing, newest first. Its price changes come from its
own posting's prices and are left out until those are known. */
export function historyOf(
	listing: TrackedPropertyModel,
	postings: readonly PostingPricesModel[] | null
): PropertyEvent[] {
	const events: PropertyEvent[] = [{ kind: 'found', at: listing.first_seen_at }];
	const ownChanges = postings?.find((posting) => posting.listing_id === listing.listing_id)?.changes ?? [];
	for (let index = 1; index < ownChanges.length; index++) {
		events.push({
			kind: 'priceChange',
			at: ownChanges[index].first_seen_at,
			from: ownChanges[index - 1].price,
			to: ownChanges[index].price
		});
	}
	if (listing.viewed_at !== null) events.push({ kind: 'viewed', at: listing.viewed_at });
	if (listing.favourited_at !== null) events.push({ kind: 'favourite', at: listing.favourited_at });
	return events.sort((a, b) => b.at.localeCompare(a.at));
}

export function pricePerM2(listing: TrackedPropertyModel): number | null {
	if (listing.price === null || listing.size_m2 === null || listing.size_m2 <= 0) return null;
	return listing.price / listing.size_m2;
}

function median(values: number[]): number {
	const sorted = [...values].sort((a, b) => a - b);
	const half = Math.floor(sorted.length / 2);
	return sorted.length % 2 === 1 ? sorted[half] : (sorted[half - 1] + sorted[half]) / 2;
}
