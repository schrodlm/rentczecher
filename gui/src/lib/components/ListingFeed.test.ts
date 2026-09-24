import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ListingFeed from './ListingFeed.svelte';
import type { components } from '$lib/api/types.gen';

type ListingModel = components['schemas']['ListingModel'];

function listing(id: string, overrides: Partial<ListingModel> = {}): ListingModel {
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

describe('ListingFeed', () => {
	test('shows the empty message when nothing is new', async () => {
		const { getByText, queryByText } = await renderWithTranslator(ListingFeed, {
			newListings: [],
			viewedListings: [],
			onviewed: () => {},
			onmarkallviewed: () => {}
		});
		expect(getByText('Žádné nové nabídky')).toBeInTheDocument();
		expect(queryByText('Označit vše jako zobrazené')).not.toBeInTheDocument();
	});

	test('reports a clicked listing as viewed', async () => {
		const onviewed = vi.fn();
		const { getByRole } = await renderWithTranslator(ListingFeed, {
			newListings: [listing('sreality:1')],
			viewedListings: [],
			onviewed,
			onmarkallviewed: () => {}
		});
		await fireEvent.click(getByRole('link'));
		expect(onviewed).toHaveBeenCalledExactlyOnceWith('sreality:1');
	});

	test('calls onmarkallviewed from the mark-all button', async () => {
		const onmarkallviewed = vi.fn();
		const { getByText } = await renderWithTranslator(ListingFeed, {
			newListings: [listing('sreality:1')],
			viewedListings: [],
			onviewed: () => {},
			onmarkallviewed
		});
		await fireEvent.click(getByText('Označit vše jako zobrazené'));
		expect(onmarkallviewed).toHaveBeenCalledOnce();
	});

	test('splits listings into the new and viewed sections', async () => {
		const { getByText } = await renderWithTranslator(ListingFeed, {
			newListings: [listing('sreality:1', { price: 21000 })],
			viewedListings: [listing('sreality:2', { price: 15000, viewed_at: '2026-09-24T10:00:00Z' })],
			onviewed: () => {},
			onmarkallviewed: () => {}
		});
		expect(getByText('Nové')).toBeInTheDocument();
		expect(getByText('Už zobrazené')).toBeInTheDocument();
		expect(getByText('21 000 Kč')).toBeInTheDocument();
		expect(getByText('15 000 Kč')).toBeInTheDocument();
	});
});
