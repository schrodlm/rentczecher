import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { TrackedPropertyModel, PostingPricesModel } from '$lib/api/client';
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
const FLAT_PRICES: PostingPricesModel[] = [
	{
		listing_id: 'bezrealitky:1',
		source: 'bezrealitky',
		url: 'https://bezrealitky.cz/1',
		changes: [
			{ price: 20500, charges: null, first_seen_at: '2026-09-14T08:00:00Z', last_seen_at: '2026-09-20T08:00:00Z' },
			{ price: 18900, charges: null, first_seen_at: '2026-09-25T08:00:00Z', last_seen_at: '2026-10-01T08:00:00Z' }
		]
	}
];

async function renderDetail(
	shown: TrackedPropertyModel = FLAT,
	preferences: ScoringPreferences | null = PREFERENCES,
	priceHistory: PostingPricesModel[] | null = FLAT_PRICES
) {
	const onfavourite = vi.fn();
	const rendered = await renderWithTranslator(ListingDetail, {
		listing: shown,
		listings: [FLAT, DEARER],
		preferences,
		priceHistory,
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

	test('shows the score as a ring', async () => {
		const { getByRole } = await renderDetail();
		expect(getByRole('img', { name: 'Skóre 87 ze 100' })).toBeInTheDocument();
	});

	test('leaves the score out while unscored', async () => {
		const { queryByText, queryByRole } = await renderDetail(FLAT, null);
		expect(queryByText(/Proč/)).toBeNull();
		expect(queryByRole('img', { name: /Skóre/ })).toBeNull();
	});

	test('compares the listing within its profile', async () => {
		const { getByText } = await renderDetail();
		expect(getByText('Nejlevnější v profilu')).toBeInTheDocument();
		expect(getByText('Nejmenší v profilu')).toBeInTheDocument();
	});

	test('lists what happened to the listing, its price changes dated', async () => {
		const { getByText } = await renderDetail();
		expect(getByText('Zlevněno z 20 500 Kč na 18 900 Kč')).toHaveTextContent('25. 9. 2026');
		expect(getByText('Poprvé nalezeno')).toBeInTheDocument();
	});

	test('names a rise in price as a rise', async () => {
		const risen: PostingPricesModel[] = [
			{ ...FLAT_PRICES[0], changes: [...FLAT_PRICES[0].changes].reverse() }
		];
		const { getByText } = await renderDetail(FLAT, PREFERENCES, risen);
		expect(getByText('Zdraženo z 18 900 Kč na 20 500 Kč')).toBeInTheDocument();
	});

	test('shows the price over time once it is known', async () => {
		const { getByRole } = await renderDetail();
		expect(getByRole('heading', { name: 'Vývoj ceny' })).toBeInTheDocument();
	});

	test('leaves the price over time out while it is not known', async () => {
		const { queryByRole } = await renderDetail(FLAT, PREFERENCES, null);
		expect(queryByRole('heading', { name: 'Vývoj ceny' })).toBeNull();
	});

	test('marks a favourite with its button', async () => {
		const { getByRole, onfavourite } = await renderDetail();
		await fireEvent.click(getByRole('button', { name: /Přidat do oblíbených/ }));
		expect(onfavourite).toHaveBeenCalledWith(true);
	});
});
