import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ListingFeed from './ListingFeed.svelte';
import { listing } from '$lib/test-support/listing';

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
