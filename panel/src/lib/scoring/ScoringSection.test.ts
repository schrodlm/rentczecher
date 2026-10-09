import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import ScoringSectionHarness from '$lib/test-support/ScoringSectionHarness.svelte';
import type { Weights } from './preferences';

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

const PREFERRED_VALUES = {
	preferred_price: 22000,
	preferred_size_m2: 70,
	preferred_land_m2: null,
	preferred_dispositions: [],
	preferred_places: [PRAHA_7]
};

const OFF: Weights = { price: 0, size: 0, land: 0, layout: 0, place: 0 };

async function renderSection(weights: Partial<Weights>, searchPlace: NamedPlace | null = PRAHA) {
	const searchPlaces = vi.fn(async () => []);
	const rendered = await renderWithTranslator(ScoringSectionHarness, {
		criteria: { ...FLAT_TO_RENT, dispositions: [] },
		searchPlace,
		preferredValues: structuredClone(PREFERRED_VALUES),
		weights: { ...OFF, ...weights },
		searchPlaces
	});
	const bound = (): Weights => JSON.parse(rendered.getByTestId('weights').textContent ?? '');
	return { searchPlaces, bound, ...rendered };
}

function bar(container: HTMLElement): string[] {
	return [...container.querySelectorAll('.split-bar__segment')].map((segment) =>
		(segment.textContent ?? '').replace(/\s+/g, ' ').trim()
	);
}

describe('ScoringSection', () => {
	test('offers the preferences that fit the estate', async () => {
		const { getAllByRole } = await renderSection({});
		expect(getAllByRole('switch').map((toggle) => toggle.getAttribute('aria-label'))).toEqual([
			'Preferovaná cena',
			'Preferovaná velikost',
			'Preferované dispozice',
			'Preferovaná místa'
		]);
	});

	test('shows the counting preferences on the split bar', async () => {
		const { container } = await renderSection({ price: 60, size: 40 });
		expect(bar(container)).toEqual(['Cena 60 %', 'Velikost 40 %']);
	});

	test('gives a switched on preference an equal share', async () => {
		const { container, getByRole, bound } = await renderSection({ price: 100 });
		await fireEvent.click(getByRole('switch', { name: 'Preferovaná velikost' }));
		expect(bound()).toMatchObject({ price: 50, size: 50 });
		expect(bar(container)).toEqual(['Cena 50 %', 'Velikost 50 %']);
	});

	test('hands back the share of a switched off preference', async () => {
		const { container, getByRole } = await renderSection({ price: 60, size: 40 });
		await fireEvent.click(getByRole('switch', { name: 'Preferovaná velikost' }));
		expect(bar(container)).toEqual(['Cena 100 %']);
	});

	test('keeps a preference without its preferred value off and out of the bar', async () => {
		const { container, getByRole } = await renderSection({ price: 70, layout: 30 });
		const layout = getByRole('switch', { name: 'Preferované dispozice' });
		expect(layout).not.toBeChecked();
		expect(layout).toBeDisabled();
		expect(bar(container)).toEqual(['Cena 100 %']);
	});

	test('waits for a first preference before showing the bar', async () => {
		const { getByText, container } = await renderSection({});
		expect(getByText('Zapněte preferenci, aby se inzeráty začaly hodnotit.')).toBeInTheDocument();
		expect(container.querySelectorAll('.split-bar')).toHaveLength(0);
	});

	test('scores example listings while a preference counts', async () => {
		const { container } = await renderSection({ price: 100 });
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
		const { getByRole } = await renderSection({}, null);
		expect(getByRole('button', { name: 'Odebrat Praha 7 (městská část, Praha)' })).toBeInTheDocument();
	});
});
