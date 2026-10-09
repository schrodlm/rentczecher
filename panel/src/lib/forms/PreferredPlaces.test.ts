import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import PreferredPlacesHarness from '$lib/test-support/PreferredPlacesHarness.svelte';

const HOLESOVICE: NamedPlace = { kind: 'cast_obce', code: 490067, name: 'Holešovice', obec: 'Praha', okres: null };
const PRAHA_7: NamedPlace = { kind: 'mestska_cast', code: 500186, name: 'Praha 7', obec: 'Praha', okres: null };

async function renderPicker(places: NamedPlace[], found: NamedPlace[] = [HOLESOVICE, PRAHA_7]) {
	const search = vi.fn(async () => found);
	const rendered = await renderWithTranslator(PreferredPlacesHarness, { places, search });
	const picked = () => JSON.parse(rendered.getByTestId('places').textContent ?? '');
	return { search, picked, input: rendered.getByRole('combobox'), ...rendered };
}

async function type(input: HTMLElement, text: string): Promise<void> {
	await fireEvent.input(input, { target: { value: text } });
	// Let the search's answer land.
	await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('PreferredPlaces', () => {
	test('adds a place picked from the search', async () => {
		const { input, getAllByRole, picked } = await renderPicker([]);
		await type(input, 'hol');
		await fireEvent.mouseDown(getAllByRole('option')[0]);
		expect(picked()).toEqual([490067]);
	});

	test('offers no place already picked', async () => {
		const { input, getAllByRole } = await renderPicker([HOLESOVICE]);
		await type(input, 'pra');
		expect(getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
			'Praha 7 (městská část, Praha)'
		]);
	});

	test('removes a picked place', async () => {
		const { getByRole, picked } = await renderPicker([HOLESOVICE, PRAHA_7]);
		await fireEvent.click(getByRole('button', { name: 'Odebrat Holešovice (část obce, Praha)' }));
		expect(picked()).toEqual([500186]);
	});
});
