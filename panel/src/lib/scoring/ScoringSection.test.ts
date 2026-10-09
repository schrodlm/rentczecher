import { fireEvent, within } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import ScoringSectionHarness from '$lib/test-support/ScoringSectionHarness.svelte';
import type { Importances } from './wishes';

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

const SETTINGS = {
	max_good_price: 22000,
	ideal_size_m2: 70,
	ideal_land_m2: null,
	preferred_dispositions: [],
	preferred_places: [PRAHA_7]
};

const OFF: Importances = { price: 0, size: 0, land: 0, layout: 0, place: 0 };

async function renderSection(importances: Partial<Importances>, searchPlace: NamedPlace | null = PRAHA) {
	const searchPlaces = vi.fn(async () => []);
	const rendered = await renderWithTranslator(ScoringSectionHarness, {
		criteria: { ...FLAT_TO_RENT, dispositions: [] },
		searchPlace,
		settings: structuredClone(SETTINGS),
		importances: { ...OFF, ...importances },
		searchPlaces
	});
	return { searchPlaces, ...rendered };
}

function legend(container: HTMLElement): string[] {
	return [...container.querySelectorAll('.scoring-section__legend li')].map((item) =>
		(item.textContent ?? '').replace(/\s+/g, ' ').trim()
	);
}

describe('ScoringSection', () => {
	test('offers the wishes that fit the estate', async () => {
		const { getAllByRole } = await renderSection({});
		expect(getAllByRole('radiogroup').map((group) => group.getAttribute('aria-label'))).toEqual([
			'Jak moc záleží na: Dobrá cena',
			'Jak moc záleží na: Správná velikost',
			'Jak moc záleží na: Dispozice, která se vám líbí',
			'Jak moc záleží na: Místo, které se vám líbí'
		]);
	});

	test('splits the score between the wishes that count', async () => {
		const { container } = await renderSection({ price: 4, size: 1 });
		expect(legend(container)).toEqual(['Dobrá cena 83 %', 'Správná velikost 17 %']);
	});

	test('reweighs the split when an importance changes', async () => {
		const { container, getByRole, getByTestId } = await renderSection({ price: 4, size: 1 });
		const size = getByRole('radiogroup', { name: 'Jak moc záleží na: Správná velikost' });
		await fireEvent.click(within(size).getByRole('radio', { name: 'Nejvíc' }));
		expect(JSON.parse(getByTestId('importances').textContent ?? '')).toMatchObject({ price: 4, size: 4 });
		expect(legend(container)).toEqual(['Dobrá cena 50 %', 'Správná velikost 50 %']);
	});

	test('keeps a wish without its setting off and out of the split', async () => {
		const { container, getByRole } = await renderSection({ price: 4, layout: 3 });
		const layout = getByRole('radiogroup', { name: 'Jak moc záleží na: Dispozice, která se vám líbí' });
		expect(within(layout).getByRole('radio', { name: 'Vypnuto' })).toBeChecked();
		expect(legend(container)).toEqual(['Dobrá cena 100 %']);
	});

	test('scores example listings while a wish counts', async () => {
		const { container } = await renderSection({ price: 4 });
		const scores = [...container.querySelectorAll('.example-card__score')].map((score) => score.textContent);
		expect(scores[0]).toBe('100');
	});

	test('scores nothing until a wish counts', async () => {
		const { getByText, container } = await renderSection({});
		expect(getByText('Dokud se nepočítá žádné přání, má každý inzerát 0 bodů.')).toBeInTheDocument();
		expect(container.querySelectorAll('.example-card')).toHaveLength(0);
	});

	test('searches preferred places only inside the search area', async () => {
		const { getByPlaceholderText, searchPlaces } = await renderSection({});
		await fireEvent.input(getByPlaceholderText('Přidat část oblasti hledání'), { target: { value: 'hol' } });
		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(searchPlaces).toHaveBeenCalledWith('hol', PRAHA, ['obvod', 'mestska_cast', 'cast_obce', 'ulice']);
	});

	test('keeps preferred places removable without a search area', async () => {
		const { getByRole } = await renderSection({}, null);
		expect(getByRole('button', { name: 'Odebrat Praha 7 (městská část, Praha)' })).toBeInTheDocument();
	});
});
