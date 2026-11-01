import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import type { Portal } from '$lib/portals';
import { renderWithTranslator } from '$lib/test-support/render';
import PortalTilesHarness from '$lib/test-support/PortalTilesHarness.svelte';

async function renderTiles(selected: Portal[]) {
	const rendered = await renderWithTranslator(PortalTilesHarness, { selected });
	const picked = () => JSON.parse(rendered.getByTestId('selected').textContent ?? '[]');
	return { picked, ...rendered };
}

/* A tile's accessible name runs its portal's name and site together. */
const tile = (name: string) => new RegExp(`^${name.replace('/', '\\/')}`);

describe('PortalTiles', () => {
	test('offers every portal with its logo and site', async () => {
		const { getAllByRole, getByText } = await renderTiles([]);
		expect(getAllByRole('button')).toHaveLength(4);
		expect(getByText('remax-czech.cz')).toBeInTheDocument();
		expect(getByText('reality.idnes.cz')).toBeInTheDocument();
		expect(getAllByRole('button').every((button) => button.querySelector('img'))).toBe(true);
	});

	test('picks a portal and drops it again', async () => {
		const { getByRole, picked } = await renderTiles(['sreality']);
		await fireEvent.click(getByRole('button', { name: tile('RE/MAX') }));
		expect(picked()).toEqual(['sreality', 'remax']);
		await fireEvent.click(getByRole('button', { name: tile('Sreality') }));
		expect(picked()).toEqual(['remax']);
	});

	test('shows the picked portals as pressed', async () => {
		const { getByRole } = await renderTiles(['bezrealitky']);
		expect(getByRole('button', { name: tile('Bezrealitky') })).toHaveAttribute('aria-pressed', 'true');
		expect(getByRole('button', { name: tile('Sreality') })).toHaveAttribute('aria-pressed', 'false');
	});

	test('turns on a portal that asks not to be read only once its note is confirmed', async () => {
		const { getByRole, getByText, queryByText, picked } = await renderTiles([]);
		await fireEvent.click(getByRole('button', { name: tile('Sreality') }));
		expect(picked()).toEqual([]);
		expect(getByText(/^Portál Sreality žádá/)).toBeInTheDocument();
		await fireEvent.click(getByRole('button', { name: 'Zapnout' }));
		expect(picked()).toEqual(['sreality']);
		expect(queryByText(/^Portál Sreality žádá/)).toBeNull();
	});

	test('leaves a portal that asks not to be read off when its note is dismissed', async () => {
		const { getByRole, queryByText, picked } = await renderTiles([]);
		await fireEvent.click(getByRole('button', { name: tile('Sreality') }));
		await fireEvent.click(getByRole('button', { name: 'Teď ne' }));
		expect(picked()).toEqual([]);
		expect(queryByText(/^Portál Sreality žádá/)).toBeNull();
	});

	test("links the portal's terms from its note", async () => {
		const { getByRole } = await renderTiles([]);
		await fireEvent.click(getByRole('button', { name: tile('Sreality') }));
		expect(getByRole('link', { name: 'Podmínky portálu Sreality' })).toHaveAttribute(
			'href',
			'https://o-seznam.cz/napoveda/sreality/smluvni-podminky-sluzby-sreality-cz/'
		);
	});

	test.each([
		['RE/MAX', 'remax'],
		['iDNES Reality', 'idnes']
	])('turns on %s, which does not ask, straight away', async (name, portal) => {
		const { getByRole, queryByRole, picked } = await renderTiles([]);
		await fireEvent.click(getByRole('button', { name: tile(name) }));
		expect(picked()).toEqual([portal]);
		expect(queryByRole('button', { name: 'Zapnout' })).toBeNull();
	});

	test('asks for a portal while none is picked', async () => {
		const { getByRole, getByText, queryByText } = await renderTiles(['sreality']);
		expect(queryByText('Vyberte aspoň jeden portál.')).toBeNull();
		await fireEvent.click(getByRole('button', { name: tile('Sreality') }));
		expect(getByText('Vyberte aspoň jeden portál.')).toBeInTheDocument();
	});
});
