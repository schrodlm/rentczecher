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
		expect(getAllByRole('button')).toHaveLength(3);
		expect(getByText('remax-czech.cz')).toBeInTheDocument();
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

	test('asks for a portal while none is picked', async () => {
		const { getByRole, getByText, queryByText } = await renderTiles(['sreality']);
		expect(queryByText('Vyberte aspoň jeden portál.')).toBeNull();
		await fireEvent.click(getByRole('button', { name: tile('Sreality') }));
		expect(getByText('Vyberte aspoň jeden portál.')).toBeInTheDocument();
	});
});
