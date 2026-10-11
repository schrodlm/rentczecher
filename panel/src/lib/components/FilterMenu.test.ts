import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import type { TrackedPropertyModel } from '$lib/api/client';
import FilterMenuHarness from '$lib/test-support/FilterMenuHarness.svelte';
import { listing } from '$lib/test-support/tracked-property';
import { renderWithTranslator } from '$lib/test-support/render';

const LISTINGS: TrackedPropertyModel[] = [
	listing('sreality:1', { source: 'sreality', disposition: '2+kk', price: 18000, size_m2: 40 }),
	listing('remax:1', { source: 'remax', disposition: '3+1', price: 26000, size_m2: 80 })
];

async function renderMenu(scored = true) {
	const rendered = await renderWithTranslator(FilterMenuHarness, { listings: LISTINGS, scored });
	const filter = () => JSON.parse(rendered.getByTestId('filter').textContent ?? '');
	await fireEvent.click(rendered.getByRole('button', { name: /Filtr/ }));
	return { filter, ...rendered };
}

describe('FilterMenu', () => {
	test('offers only the portals and layouts the listings have', async () => {
		const { getByRole } = await renderMenu();
		const portals = getByRole('group', { name: 'Portály' });
		expect(portals.textContent).toContain('Sreality');
		expect(portals.textContent).toContain('RE/MAX');
		expect(portals.textContent).not.toContain('Bezrealitky');
		const layouts = getByRole('group', { name: 'Dispozice' });
		expect([...layouts.querySelectorAll('button')].map((chip) => chip.textContent?.trim())).toEqual(['2+kk', '3+1']);
	});

	test('writes the chosen portal and price drops into the filter and counts them', async () => {
		const { getByRole, filter } = await renderMenu();
		await fireEvent.click(getByRole('button', { name: 'RE/MAX' }));
		await fireEvent.click(getByRole('checkbox', { name: 'Jen zlevněné' }));
		expect(filter()).toMatchObject({ portals: ['remax'], onlyPriceDrops: true });
		expect(getByRole('button', { name: /Filtr/ })).toHaveTextContent('2');
	});

	test('clears every part at once', async () => {
		const { getByRole, filter } = await renderMenu();
		await fireEvent.click(getByRole('checkbox', { name: 'Jen zlevněné' }));
		await fireEvent.click(getByRole('button', { name: 'Zrušit filtr' }));
		expect(filter().onlyPriceDrops).toBe(false);
	});

	test('offers no score while the listings go unscored', async () => {
		const { queryByRole } = await renderMenu(false);
		expect(queryByRole('group', { name: 'Skóre alespoň' })).toBeNull();
	});

	test('closes with Escape', async () => {
		const { queryByRole } = await renderMenu();
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(queryByRole('dialog', { name: 'Filtr' })).toBeNull();
	});
});
