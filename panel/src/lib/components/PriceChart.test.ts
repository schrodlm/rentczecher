import { describe, expect, test } from 'vitest';
import type { PostingPricesModel } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import PriceChart from './PriceChart.svelte';

function posting(listingId: string, prices: number[]): PostingPricesModel {
	return {
		listing_id: listingId,
		source: listingId.split(':')[0],
		url: `https://example.invalid/${listingId}`,
		changes: prices.map((price, index) => ({
			price,
			charges: null,
			first_seen_at: `2026-10-0${index + 1}T08:00:00Z`,
			last_seen_at: `2026-10-0${index + 1}T08:00:00Z`
		}))
	};
}

function text(container: HTMLElement): string {
	return (container.textContent ?? '').replace(/\s/g, ' ');
}

describe('PriceChart', () => {
	test('names the highest and lowest price a changed listing asked', async () => {
		const { container } = await renderWithTranslator(PriceChart, {
			postings: [posting('sreality:1', [25500, 24000])],
			ownListingId: 'sreality:1'
		});
		expect(text(container)).toContain('25 500 Kč');
		expect(text(container)).toContain('24 000 Kč');
		expect(text(container)).not.toContain('nezměnila');
	});

	test('names an unchanged price once and says since when', async () => {
		const { container } = await renderWithTranslator(PriceChart, {
			postings: [posting('remax:1', [19500, 19500])],
			ownListingId: 'remax:1'
		});
		expect(text(container).match(/19 500 Kč/g)).toHaveLength(1);
		expect(text(container)).toContain('Cena se nezměnila od 1. 10.');
	});

	test('keys each portal’s line to its current price when more than one carries the flat', async () => {
		const { getAllByRole } = await renderWithTranslator(PriceChart, {
			postings: [posting('bezrealitky:1', [25500, 24000]), posting('sreality:1', [24900])],
			ownListingId: 'bezrealitky:1'
		});
		const keys = getAllByRole('listitem').map((item) => item.textContent?.replace(/\s+/g, ' ').trim());
		expect(keys).toEqual(['Bezrealitky · 24 000 Kč', 'Sreality · 24 900 Kč']);
	});

	test('shows no key for a flat on one portal', async () => {
		const { queryAllByRole } = await renderWithTranslator(PriceChart, {
			postings: [posting('sreality:1', [25500, 24000])],
			ownListingId: 'sreality:1'
		});
		expect(queryAllByRole('listitem')).toHaveLength(0);
	});
});
