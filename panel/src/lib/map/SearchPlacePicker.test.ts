import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import SearchPlacePicker from './SearchPlacePicker.svelte';

const KDYNE: NamedPlace = { kind: 'obec', code: 553786, name: 'Kdyně', obec: null, okres: 'Domažlice' };

async function renderPicker(place: NamedPlace | null = null) {
	const search = vi.fn(async () => [KDYNE]);
	const onchange = vi.fn();
	const rendered = await renderWithTranslator(SearchPlacePicker, { search, place, onchange });
	return { search, onchange, ...rendered };
}

describe('SearchPlacePicker', () => {
	test('says no place is picked yet', async () => {
		const { getByText } = await renderPicker();
		expect(getByText('Zatím není vybráno žádné místo')).toBeInTheDocument();
	});

	test('picks a place found by name and shows it on the map', async () => {
		const { getByRole, getAllByRole, onchange } = await renderPicker();
		const input = getByRole('combobox');
		await fireEvent.input(input, { target: { value: 'kd' } });
		await new Promise((resolve) => setTimeout(resolve, 0));
		await fireEvent.mouseDown(getAllByRole('option')[0]);
		expect(onchange).toHaveBeenCalledWith(KDYNE);
		expect(getByRole('button', { name: 'Plzeňský kraj' })).toBeInTheDocument();
		expect(getByRole('button', { name: 'Zpět' })).toBeEnabled();
	});

	test('names the picked place and clears it', async () => {
		const { getByRole, onchange } = await renderPicker(KDYNE);
		expect(getByRole('button', { name: 'Kdyně (obec, Domažlice)' })).toBeInTheDocument();
		await fireEvent.click(getByRole('button', { name: 'Zrušit místo' }));
		expect(onchange).toHaveBeenCalledWith(null);
	});

	test('brings the picked place into view when its name is clicked', async () => {
		const { getByRole } = await renderPicker(KDYNE);
		await fireEvent.click(getByRole('button', { name: 'Kdyně (obec, Domažlice)' }));
		expect(getByRole('button', { name: 'Plzeňský kraj' })).toBeInTheDocument();
	});

	test('passes a pick on the map through', async () => {
		const { container, onchange } = await renderPicker();
		const plzensky = [...container.querySelectorAll('.czech-map__kraj')].find(
			(path) => path.textContent === 'Plzeňský kraj'
		)!;
		await fireEvent.click(plzensky);
		const whole = [...container.querySelectorAll('button')].find(
			(button) => button.textContent?.trim() === 'Hledat v celé oblasti'
		)!;
		await fireEvent.click(whole);
		expect(onchange).toHaveBeenCalledWith(expect.objectContaining({ kind: 'kraj', code: 43 }));
	});
});
