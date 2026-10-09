import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import ScoringSectionHarness from '$lib/test-support/ScoringSectionHarness.svelte';
import type { PreferredValues, Weights } from './preferences';

const PRAHA: NamedPlace = { kind: 'obec', code: 554782, name: 'Praha', obec: null, okres: null };
const PRAHA_7: NamedPlace = { kind: 'mestska_cast', code: 500186, name: 'Praha 7', obec: 'Praha', okres: null };

const FLAT_TO_RENT = {
	estate_type: 'flat',
	offer_type: 'rent',
	min_price: null,
	max_price: null,
	min_size_m2: null,
	max_size_m2: null,
	min_land_m2: null,
	dispositions: []
} as const;

const NO_VALUES: PreferredValues = {
	preferred_price: null,
	preferred_size_m2: null,
	preferred_land_m2: null,
	preferred_dispositions: [],
	preferred_places: []
};

const OFF: Weights = { price: 0, size: 0, land: 0, layout: 0, place: 0 };

async function renderSection(
	values: Partial<PreferredValues>,
	weights: Partial<Weights> = {},
	searchPlace: NamedPlace | null = PRAHA
) {
	const searchPlaces = vi.fn(async () => []);
	const rendered = await renderWithTranslator(ScoringSectionHarness, {
		criteria: { ...FLAT_TO_RENT, dispositions: [] },
		searchPlace,
		preferredValues: { ...NO_VALUES, ...values },
		weights: { ...OFF, ...weights },
		searchPlaces
	});
	return { searchPlaces, ...rendered };
}

function bar(container: HTMLElement): string[] {
	return [...container.querySelectorAll('.split-bar__segment')].map((segment) =>
		(segment.textContent ?? '').replace(/\s+/g, ' ').trim()
	);
}

describe('ScoringSection', () => {
	test('offers the preferences that fit the estate', async () => {
		const { container } = await renderSection({});
		const titles = [...container.querySelectorAll('.preference-card__title')].map((title) => title.textContent);
		expect(titles).toEqual(['Preferovaná cena', 'Preferovaná velikost', 'Preferované dispozice', 'Preferovaná místa']);
	});

	test('shows the counting preferences on the split bar', async () => {
		const { container } = await renderSection({ preferred_price: 22000, preferred_size_m2: 70 }, { price: 60, size: 40 });
		expect(bar(container)).toEqual(['Cena 60 %', 'Velikost 40 %']);
	});

	test('counts a preference as soon as its preferred value is set', async () => {
		const { container, getByRole } = await renderSection({ preferred_price: 22000 }, { price: 100 });
		await fireEvent.click(getByRole('button', { name: '2+kk' }));
		expect(bar(container)).toEqual(['Cena 50 %', 'Dispozice 50 %']);
	});

	test('stops counting a preference whose preferred value is cleared', async () => {
		const values = { preferred_price: 22000, preferred_dispositions: ['2+kk' as const] };
		const { container, getByRole } = await renderSection(values, { price: 60, layout: 40 });
		await fireEvent.click(getByRole('button', { name: '2+kk' }));
		expect(bar(container)).toEqual(['Cena 100 %']);
	});

	test('leaves a preference without its preferred value muted and out of the bar', async () => {
		const { container } = await renderSection({ preferred_price: 22000 }, { price: 100 });
		const muted = [...container.querySelectorAll('.preference-card--off .preference-card__title')];
		expect(muted.map((title) => title.textContent)).toEqual([
			'Preferovaná velikost',
			'Preferované dispozice',
			'Preferovaná místa'
		]);
		expect(bar(container)).toEqual(['Cena 100 %']);
	});

	test('names the points each preference is worth in its rule', async () => {
		const values = { preferred_price: 22000, preferred_places: [PRAHA_7] };
		const { getByText } = await renderSection(values, { price: 80, place: 20 });
		expect(getByText('Všech 80 bodů do 22 000 Kč, od 44 000 Kč žádné.')).toBeInTheDocument();
		expect(getByText('Všech 20 bodů v kterémkoli z těchto míst, jinde žádné.')).toBeInTheDocument();
	});

	test('waits for a first preferred value before showing the bar', async () => {
		const { getByText, container } = await renderSection({});
		expect(getByText('Nastavte preferovanou hodnotu, aby se inzeráty začaly hodnotit.')).toBeInTheDocument();
		expect(container.querySelectorAll('.split-bar')).toHaveLength(0);
	});

	test('scores example listings while a preference counts', async () => {
		const { container } = await renderSection({ preferred_price: 22000 }, { price: 100 });
		const scores = [...container.querySelectorAll('.example-card__score')].map((score) => score.textContent);
		expect(scores[0]).toBe('100');
	});

	test('scores nothing until a preference counts', async () => {
		const { getByText, container } = await renderSection({});
		expect(getByText('Dokud se nepočítá žádná preference, má každý inzerát 0 bodů.')).toBeInTheDocument();
		expect(container.querySelectorAll('.example-card')).toHaveLength(0);
	});

	test('searches preferred places only inside the search area', async () => {
		const { getByPlaceholderText, searchPlaces } = await renderSection({});
		await fireEvent.input(getByPlaceholderText('Přidat část oblasti hledání'), { target: { value: 'hol' } });
		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(searchPlaces).toHaveBeenCalledWith('hol', PRAHA, ['obvod', 'mestska_cast', 'cast_obce', 'ulice']);
	});

	test('keeps preferred places removable without a search area', async () => {
		const { getByRole } = await renderSection({ preferred_places: [PRAHA_7] }, {}, null);
		expect(getByRole('button', { name: 'Odebrat Praha 7 (městská část, Praha)' })).toBeInTheDocument();
	});
});
