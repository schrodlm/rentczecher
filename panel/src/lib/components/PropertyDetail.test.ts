import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { GalleryModel, TrackedPropertyModel, PostingPricesModel } from '$lib/api/client';
import type { ScoringPreferences } from '$lib/scoring/score';
import { trackedProperty } from '$lib/test-support/tracked-property';
import { renderWithTranslator } from '$lib/test-support/render';
import { PRAHA_7 } from '$lib/welcome/sample-flats';
import PropertyDetail from './PropertyDetail.svelte';

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

const FLAT = trackedProperty('bezrealitky:1', {
	source: 'bezrealitky',
	price: 18900,
	size_m2: 41,
	price_drop_from: 20500,
	first_seen_at: '2026-09-14T08:00:00Z',
	sibling_sources: [{ source: 'sreality', url: 'https://sreality.cz/detail/9' }]
});
const DEARER = trackedProperty('sreality:2', { price: 25000, size_m2: 70 });
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
	const rendered = await renderWithTranslator(PropertyDetail, {
		listing: shown,
		listings: [FLAT, DEARER],
		preferences,
		priceHistory,
		gallery: null,
		onfavourite
	});
	return { onfavourite, ...rendered };
}

describe('PropertyDetail', () => {
	test('heads the details with the index, the place and the price, and its picture', async () => {
		const { container } = await renderDetail(trackedProperty('sreality:7', {
			index: 124,
			resolved_location: null,
			location_raw_text: 'Praha 7',
			price: 23000,
			main_photo: { url: 'http://127.0.0.1:1/a.jpg?sig=s' }
		}));
		const title = container.querySelector('.property-detail__title');
		expect(title?.querySelector('.property-detail__index')).toHaveTextContent('#124');
		expect(title).toHaveTextContent('Praha 7');
		expect(title?.querySelector('.property-detail__price')?.textContent?.replace(/\s/g, ' ')).toBe('23 000 Kč');
		expect(container.querySelector('.property-detail__picture .property-picture__photo')).toHaveAttribute(
			'src',
			'http://127.0.0.1:1/a.jpg?sig=s'
		);
	});

	test('leads with the photos of its gallery', async () => {
		const gallery: GalleryModel = {
			status: 'stored',
			source: 'bezrealitky',
			posting_url: 'https://bezrealitky.cz/1',
			photo_count: 2,
			photos: [{ url: 'http://127.0.0.1:1/a.jpg' }, { url: 'http://127.0.0.1:1/b.jpg' }]
		};
		const { container } = await renderWithTranslator(PropertyDetail, {
			listing: FLAT,
			listings: [FLAT, DEARER],
			preferences: PREFERENCES,
			priceHistory: FLAT_PRICES,
			gallery,
			onfavourite: vi.fn()
		});
		const first = container.querySelector('.property-detail')?.firstElementChild;
		expect(first).toHaveClass('photo-collage');
		expect(first?.querySelectorAll('img')).toHaveLength(2);
	});

	test('shows no photos before its gallery loads', async () => {
		const { container } = await renderDetail();
		expect(container.querySelector('.photo-collage, .photo-collage__empty')).toBeNull();
	});

	test('shows a listing with a point on a street map of its own, beside the place map, crediting both', async () => {
		const { container, getByRole } = await renderDetail(trackedProperty('sreality:4', {
			resolved_location: PRAHA_7,
			point: { lat: 50.1, lon: 14.44 }
		}));
		expect(container.querySelector('.street-map')).not.toBeNull();
		expect(getByRole('link', { name: 'ČÚZK, 2026' })).toBeInTheDocument();
		expect(getByRole('link', { name: '© přispěvatelé OpenStreetMap' })).toBeInTheDocument();
	});

	test('opens the street map over the whole window and closes it', async () => {
		const { getByLabelText, queryByRole } = await renderDetail(trackedProperty('sreality:4', {
			resolved_location: PRAHA_7,
			point: { lat: 50.1, lon: 14.44 }
		}));
		await fireEvent.click(getByLabelText('Otevřít mapu přes celé okno'));
		expect(queryByRole('dialog')).not.toBeNull();
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(queryByRole('dialog')).toBeNull();
	});

	test('links a listing with a point to Mapy.cz and Google Maps', async () => {
		const { getByRole } = await renderDetail(trackedProperty('sreality:4', {
			resolved_location: PRAHA_7,
			point: { lat: 50.1, lon: 14.44 }
		}));
		expect(getByRole('link', { name: 'Mapy.cz ↗' })).toHaveAttribute('href', expect.stringContaining('center=14.44,50.1'));
		expect(getByRole('link', { name: 'Google Maps ↗' })).toHaveAttribute('href', expect.stringContaining('query=50.1,14.44'));
	});

	test('shows a listing without a point on the place map alone', async () => {
		const { container, queryByRole } = await renderDetail(trackedProperty('bezrealitky:5', {
			resolved_location: PRAHA_7,
			point: null
		}));
		expect(container.querySelector('.street-map')).toBeNull();
		expect(queryByRole('link', { name: '© přispěvatelé OpenStreetMap' })).toBeNull();
		expect(queryByRole('link', { name: 'Mapy.cz ↗' })).toBeNull();
	});

	test('credits ČÚZK under the map of where the listing lies', async () => {
		const located = trackedProperty('bezrealitky:3', {
			resolved_location: {
				kraj: { code: 19, name: 'Hlavní město Praha' },
				okres: null,
				obec: { code: 554782, name: 'Praha' },
				obvod: { code: 78, name: 'Praha 7' },
				mestska_cast: null,
				cast_obce: null,
				ulice: null,
				cislo_popisne: null,
				cislo_orientacni: null
			}
		});
		const { getByRole } = await renderDetail(located);
		expect(getByRole('link', { name: 'ČÚZK, 2026' })).toBeInTheDocument();
		expect(getByRole('link', { name: 'CC BY 4.0' })).toBeInTheDocument();
	});

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
