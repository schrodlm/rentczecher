import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import CzechMap from './CzechMap.svelte';
import { MapNavigation } from './navigation.svelte';

const PRAHA_7: NamedPlace = { kind: 'obvod', code: 78, name: 'Praha 7', obec: 'Praha', okres: null };

async function renderMap(picked: NamedPlace | null = null) {
	const navigation = new MapNavigation();
	const onpick = vi.fn();
	const rendered = await renderWithTranslator(CzechMap, { navigation, picked, onpick });
	return { navigation, onpick, ...rendered };
}

/* The drawn shape named by its title, which is how the map names its regions. */
function shape(container: HTMLElement, selector: string, title: string): Element {
	const found = [...container.querySelectorAll(selector)].find((element) => element.textContent === title);
	if (!found) throw new Error(`no ${selector} titled ${title}`);
	return found;
}

describe('CzechMap', () => {
	test('opens a kraj when it is clicked', async () => {
		const { container, getByRole, navigation } = await renderMap();
		await fireEvent.click(shape(container, '.czech-map__kraj', 'Plzeňský kraj'));
		expect(navigation.kraj?.name).toBe('Plzeňský kraj');
		expect(getByRole('button', { name: 'Plzeňský kraj' })).toHaveAttribute('aria-current', 'location');
	});

	test('can go back only once it has moved in', async () => {
		const { container, getByRole } = await renderMap();
		const back = getByRole('button', { name: 'Zpět' });
		expect(back).toBeDisabled();
		await fireEvent.click(shape(container, '.czech-map__kraj', 'Plzeňský kraj'));
		expect(back).toBeEnabled();
	});

	test('picks a town, and clears it when the picked town is clicked again', async () => {
		const { container, onpick, navigation, rerender } = await renderMap();
		await fireEvent.click(shape(container, '.czech-map__kraj', 'Plzeňský kraj'));
		await fireEvent.click(shape(container, '.czech-map__district', 'Domažlice'));
		await fireEvent.click(shape(container, '.czech-map__town', 'Kdyně'));
		const kdyne = onpick.mock.calls[0][0];
		expect(kdyne).toMatchObject({ kind: 'obec', name: 'Kdyně', okres: 'Domažlice' });

		await rerender({ navigation, picked: kdyne, onpick });
		await fireEvent.click(shape(container, '.czech-map__town', 'Kdyně'));
		expect(onpick).toHaveBeenLastCalledWith(null);
	});

	test('picks the whole area in view, and clears it again', async () => {
		const { container, getByRole, onpick, navigation, rerender } = await renderMap();
		await fireEvent.click(shape(container, '.czech-map__kraj', 'Plzeňský kraj'));
		await fireEvent.click(getByRole('button', { name: 'Hledat v celé oblasti' }));
		const plzensky = onpick.mock.calls[0][0];
		expect(plzensky).toMatchObject({ kind: 'kraj', code: 43 });

		await rerender({ navigation, picked: plzensky, onpick });
		await fireEvent.click(getByRole('button', { name: 'Hledá se v celé oblasti' }));
		expect(onpick).toHaveBeenLastCalledWith(null);
	});

	test('picks a Praha obvod from inside Praha', async () => {
		const { container, onpick } = await renderMap();
		await fireEvent.click(shape(container, '.czech-map__kraj', 'Hlavní město Praha'));
		await fireEvent.click(shape(container, '.czech-map__district', 'Praha 7'));
		expect(onpick).toHaveBeenCalledWith(PRAHA_7);
	});

	test('marks a picked Praha obvod over the whole country too', async () => {
		const { container } = await renderMap(PRAHA_7);
		expect(container.querySelector('.czech-map__picked-outline')).not.toBeNull();
	});

	test('tells what a click does at each level', async () => {
		const { container, getByText } = await renderMap();
		expect(getByText('Klikněte na oblast a přibližte ji.')).toBeInTheDocument();
		await fireEvent.click(shape(container, '.czech-map__kraj', 'Hlavní město Praha'));
		expect(getByText('Klikněte na pražský obvod a hledejte v něm.')).toBeInTheDocument();
	});
});
