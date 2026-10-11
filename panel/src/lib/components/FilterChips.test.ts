import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import { noFilter, type PropertyFilter } from '$lib/property-filter';
import FilterChipsHarness from '$lib/test-support/FilterChipsHarness.svelte';
import { renderWithTranslator } from '$lib/test-support/render';

const FILTER: PropertyFilter = {
	...noFilter(),
	portals: ['sreality', 'remax'],
	onlyPriceDrops: true,
	minimumScore: 60,
	minPrice: 15000,
	maxPrice: 25000,
	maxSize: 60
};

async function renderChips(filter: PropertyFilter = FILTER) {
	const rendered = await renderWithTranslator(FilterChipsHarness, { filter, shown: 3, count: 7 });
	const written = () => JSON.parse(rendered.getByTestId('filter').textContent ?? '');
	return { written, ...rendered };
}

function text(element: Element): string {
	return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

describe('FilterChips', () => {
	test('names each active part and says how many listings it shows', async () => {
		const { getAllByRole, getByText } = await renderChips();
		expect(getAllByRole('button').map(text)).toEqual([
			'Sreality, RE/MAX ×',
			'Jen zlevněné ×',
			'Skóre od 60 ×',
			'15 000 Kč – 25 000 Kč ×',
			'do 60 m² ×'
		]);
		expect(getByText('Zobrazeno 3 z 7')).toBeInTheDocument();
	});

	test('clears only the part its chip names', async () => {
		const { getByRole, written } = await renderChips();
		await fireEvent.click(getByRole('button', { name: 'Zrušit Jen zlevněné' }));
		expect(written()).toEqual({ ...FILTER, onlyPriceDrops: false });
	});

	test('shows nothing while the filter is empty', async () => {
		const { queryByText, queryAllByRole } = await renderChips(noFilter());
		expect(queryAllByRole('button')).toHaveLength(0);
		expect(queryByText(/Zobrazeno/)).toBeNull();
	});
});
