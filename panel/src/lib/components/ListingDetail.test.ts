import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { ListingModel } from '$lib/api/client';
import type { ScoringPreferences } from '$lib/scoring/score';
import { listing } from '$lib/test-support/listing';
import { renderWithTranslator } from '$lib/test-support/render';
import ListingDetail from './ListingDetail.svelte';

const PREFERENCES: ScoringPreferences = {
	price_per_m2_weight: 0,
	disposition_weight: 0,
	preferred_dispositions: [],
	size_weight: 40,
	preferred_size_m2: 60,
	place_weight: 0,
	preferred_places: [],
	land_weight: 0,
	preferred_land_m2: null,
	price_weight: 60,
	preferred_price: 22000
};

const FLAT = listing('bezrealitky:1', {
	source: 'bezrealitky',
	price: 18900,
	size_m2: 41,
	price_drop_from: 20500,
	first_seen_at: '2026-09-14T08:00:00Z',
	sibling_sources: [{ source: 'sreality', url: 'https://sreality.cz/detail/9' }]
});
const DEARER = listing('sreality:2', { price: 25000, size_m2: 70 });

async function renderDetail(shown: ListingModel = FLAT, preferences: ScoringPreferences | null = PREFERENCES) {
	const onfavourite = vi.fn();
	const rendered = await renderWithTranslator(ListingDetail, {
		listing: shown,
		listings: [FLAT, DEARER],
		preferences,
		onfavourite
	});
	return { onfavourite, ...rendered };
}

describe('ListingDetail', () => {
	test('links to every portal carrying the listing', async () => {
		const { getByRole } = await renderDetail();
		expect(getByRole('link', { name: 'Otevřít na Bezrealitky ↗' })).toBeInTheDocument();
		expect(getByRole('link', { name: 'také na Sreality ↗' })).toHaveAttribute('href', 'https://sreality.cz/detail/9');
	});

	test('explains the score by each preference against the preferred value', async () => {
		const { getByText } = await renderDetail();
		expect(getByText('Proč 87 bodů')).toBeInTheDocument();
		expect(getByText('41 m² · preferováno 60 m²')).toBeInTheDocument();
		expect(getByText('18 900 Kč · preferováno do 22 000 Kč')).toBeInTheDocument();
	});

	test('leaves the score out while unscored', async () => {
		const { queryByText } = await renderDetail(FLAT, null);
		expect(queryByText(/Proč/)).toBeNull();
	});

	test('compares the listing within its profile', async () => {
		const { getByText } = await renderDetail();
		expect(getByText('Nejlevnější v profilu')).toBeInTheDocument();
		expect(getByText('Nejmenší v profilu')).toBeInTheDocument();
	});

	test('lists what happened to the listing', async () => {
		const { getByText } = await renderDetail();
		expect(getByText('Zlevněno z 20 500 Kč na 18 900 Kč')).toBeInTheDocument();
		expect(getByText('Poprvé nalezeno')).toBeInTheDocument();
	});

	test('marks a favourite with its button', async () => {
		const { getByRole, onfavourite } = await renderDetail();
		await fireEvent.click(getByRole('button', { name: /Přidat do oblíbených/ }));
		expect(onfavourite).toHaveBeenCalledWith(true);
	});
});
