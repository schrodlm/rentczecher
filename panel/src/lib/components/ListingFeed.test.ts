import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ListingFeed from './ListingFeed.svelte';
import { listing } from '$lib/test-support/listing';

describe('ListingFeed', () => {
	test('shows the empty message when nothing is new', async () => {
		const { getByText, queryByText } = await renderWithTranslator(ListingFeed, {
			preferences: null,
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
			preferences: null,
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
			preferences: null,
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
			preferences: null,
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

	test('scores every listing by the profile\'s preferences', async () => {
		const preferences = {
			price_per_m2_weight: 0,
			disposition_weight: 0,
			preferred_dispositions: [],
			size_weight: 0,
			preferred_size_m2: null,
			place_weight: 0,
			preferred_places: [],
			land_weight: 0,
			preferred_land_m2: null,
			price_weight: 100,
			preferred_price: 21000
		};
		const { getAllByRole } = await renderWithTranslator(ListingFeed, {
			newListings: [listing('sreality:1', { price: 21000 })],
			viewedListings: [listing('sreality:2', { price: 31500, viewed_at: new Date().toISOString() })],
			preferences,
			onviewed: () => {},
			onmarkallviewed: () => {}
		});
		expect(getAllByRole('img', { name: /Skóre/ }).map((ring) => ring.getAttribute('aria-label'))).toEqual([
			'Skóre 100 ze 100',
			'Skóre 50 ze 100'
		]);
	});

	test('sorts by score and offers no score while unscored', async () => {
		const preferences = {
			price_per_m2_weight: 0,
			disposition_weight: 0,
			preferred_dispositions: [],
			size_weight: 0,
			preferred_size_m2: null,
			place_weight: 0,
			preferred_places: [],
			land_weight: 0,
			preferred_land_m2: null,
			price_weight: 100,
			preferred_price: 20000
		};
		const cheap = listing('sreality:1', { price: 20000, first_seen_at: '2026-10-01T00:00:00Z' });
		const dear = listing('sreality:2', { price: 30000, first_seen_at: '2026-10-02T00:00:00Z' });
		const props = { newListings: [dear, cheap], viewedListings: [], onviewed: () => {}, onmarkallviewed: () => {} };
		const scored = await renderWithTranslator(ListingFeed, { ...props, preferences });
		expect(scored.getAllByRole('img', { name: /Skóre/ }).map((ring) => ring.getAttribute('aria-label'))).toEqual([
			'Skóre 100 ze 100',
			'Skóre 50 ze 100'
		]);
		scored.unmount();
		const unscored = await renderWithTranslator(ListingFeed, { ...props, preferences: null });
		expect(unscored.getByRole('button', { name: 'Řadit podle: Datum' })).toBeInTheDocument();
	});
});
