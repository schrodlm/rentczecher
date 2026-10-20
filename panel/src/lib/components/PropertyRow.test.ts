import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { trackedProperty } from '$lib/test-support/tracked-property';
import { renderWithTranslator } from '$lib/test-support/render';
import PropertyRow from './PropertyRow.svelte';

async function renderRow(overrides = {}, score: number | null = 78, selected = false) {
	const onselect = vi.fn();
	const rendered = await renderWithTranslator(PropertyRow, {
		listing: trackedProperty('sreality:1', { price: 21500, size_m2: 54, location_raw_text: 'Praha 7', ...overrides }),
		id: 'row-sreality:1',
		score,
		selected,
		onselect
	});
	return { onselect, ...rendered };
}

describe('PropertyRow', () => {
	test('names the flat by its index and place before its price', async () => {
		const { container } = await renderRow({ index: 124, resolved_location: null, location_raw_text: 'Praha 7' });
		expect(container.querySelector('.property-row__name')).toHaveTextContent('#124 Praha 7');
		expect(container.querySelector('.property-row__price')).toHaveTextContent('21 500 Kč');
	});

	test('pictures the flat by its main photo', async () => {
		const { container } = await renderRow({ main_photo: { url: 'http://127.0.0.1:1/a.jpg?sig=s' } });
		expect(container.querySelector('.property-picture__photo')).toHaveAttribute('src', 'http://127.0.0.1:1/a.jpg?sig=s');
	});

	test('shows the price, the facts and the score', async () => {
		const { getByRole } = await renderRow();
		const row = getByRole('option');
		expect(row).toHaveTextContent('21 500 Kč');
		expect(row).toHaveTextContent('2+kk · 54 m²');
		expect(row).toHaveTextContent('78');
	});

	test('reports a click as wanting to be selected', async () => {
		const { getByRole, onselect } = await renderRow();
		await fireEvent.click(getByRole('option'));
		expect(onselect).toHaveBeenCalledOnce();
	});

	test('leaves the focus to the list around it', async () => {
		const { getByRole } = await renderRow();
		expect(getByRole('option')).not.toHaveAttribute('tabindex');
	});

	test('says whether it is the selected one', async () => {
		const { getByRole } = await renderRow({}, 78, true);
		expect(getByRole('option')).toHaveAttribute('aria-selected', 'true');
	});

	test('stars a favourite and shows no score while unscored', async () => {
		const { getByLabelText, getByRole } = await renderRow({ favourited_at: '2026-10-09T08:00:00Z' }, null);
		expect(getByLabelText('Oblíbený')).toBeInTheDocument();
		expect(getByRole('option')).not.toHaveTextContent('78');
	});
});
