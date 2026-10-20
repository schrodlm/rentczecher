import { fireEvent } from '@testing-library/svelte';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import type { Box, NearbyPlace } from './geometry';
import type { NearbyKindShown } from './kinds';
import NearbyBox from './NearbyBox.svelte';
import { NearbyStore } from './nearby-store.svelte';

const FLAT = { lat: 50.1, lon: 14.44 };

class AnsweringOverpass {
	async places(kind: NearbyKindShown, _box: Box): Promise<NearbyPlace[]> {
		return kind.kind === 'metro' ? [{ name: 'Vltavská', point: { lat: 50.1002, lon: 14.4385 } }] : [];
	}
}

function storeShowing(...kinds: Parameters<NearbyStore['toggle']>[0][]): NearbyStore {
	const store = new NearbyStore(new AnsweringOverpass());
	store.show('p1', [FLAT]);
	for (const kind of kinds) store.toggle(kind);
	return store;
}

beforeEach(() => {
	localStorage.clear();
});

describe('NearbyBox', () => {
	test("shows the nearest of each of the profile's kinds and how far it is", async () => {
		const { container } = await renderWithTranslator(NearbyBox, { nearby: storeShowing('metro'), point: FLAT });
		await vi.waitFor(() => expect(container.querySelector('.nearby-box__place')).toHaveTextContent('Vltavská'));
		expect(container.querySelector('.nearby-box__kind')).toHaveTextContent('Metro');
		expect(container.querySelector('.nearby-box__distance')?.textContent?.replace(/\s/g, ' ')).toBe('110 m');
	});

	test('opens every kind to choose from, saying it is for the whole profile', async () => {
		const { getByRole, getByText, getAllByRole } = await renderWithTranslator(NearbyBox, {
			nearby: storeShowing(),
			point: FLAT
		});
		await fireEvent.click(getByRole('button', { name: /Vybrat, co v okolí měřit/ }));
		expect(getByText('Zobrazí se u všech bytů tohoto profilu.')).toBeInTheDocument();
		expect(getAllByRole('checkbox')).toHaveLength(11);
	});

	test('switches a kind on and off for the profile', async () => {
		const store = storeShowing();
		const { getByRole, getByLabelText } = await renderWithTranslator(NearbyBox, { nearby: store, point: FLAT });
		await fireEvent.click(getByRole('button', { name: /Vybrat, co v okolí měřit/ }));
		await fireEvent.click(getByLabelText('Lékárna'));
		expect(store.chosen).toEqual(['pharmacy']);
		await fireEvent.click(getByLabelText('Lékárna'));
		expect(store.chosen).toEqual([]);
	});

	test('closes the list when done', async () => {
		const { getByRole, queryAllByRole } = await renderWithTranslator(NearbyBox, { nearby: storeShowing(), point: FLAT });
		await fireEvent.click(getByRole('button', { name: /Vybrat, co v okolí měřit/ }));
		await fireEvent.click(getByRole('button', { name: 'Hotovo' }));
		expect(queryAllByRole('checkbox')).toHaveLength(0);
	});

	test('says a flat without an exact location can be measured to nothing', async () => {
		const { getByText } = await renderWithTranslator(NearbyBox, { nearby: storeShowing('metro'), point: null });
		expect(getByText('Bez přesné polohy nelze nic změřit.')).toBeInTheDocument();
	});
});
