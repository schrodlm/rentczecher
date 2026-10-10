import { fireEvent, within } from '@testing-library/svelte';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import type { ScoringPreferences } from '$lib/scoring/score';
import InboxHarness from '$lib/test-support/InboxHarness.svelte';
import { listing } from '$lib/test-support/listing';
import { renderWithTranslator } from '$lib/test-support/render';

const PREFERENCES: ScoringPreferences = {
	price_per_m2_weight: 0,
	disposition_weight: 0,
	preferred_dispositions: [],
	size_weight: 0,
	preferred_size_m2: null,
	place_weight: 0,
	preferred_places: [],
	land_weight: 0,
	preferred_land_m2: null,
	price_weight: 100,
	preferred_price: 20000
};

function flats() {
	return [
		listing('a', { price: 20000 }),
		listing('b', { price: 25000 }),
		listing('c', { price: 30000, viewed_at: '2026-10-01T00:00:00Z' })
	];
}

async function renderInbox() {
	const onview = vi.fn();
	const onfavourite = vi.fn();
	const rendered = await renderWithTranslator(InboxHarness, {
		listings: flats(),
		preferences: PREFERENCES,
		onview,
		onfavourite
	});
	const section = (name: string) => rendered.getByRole('group', { name });
	const prices = (name: string) =>
		within(section(name))
			.getAllByRole('option')
			.map((row) => row.querySelector('.listing-row__price')?.textContent?.replace(/\s/g, ' '));
	return { onview, onfavourite, section, prices, listbox: rendered.getByRole('listbox'), ...rendered };
}

beforeEach(() => {
	Element.prototype.scrollIntoView = vi.fn();
});

describe('Inbox', () => {
	test('opens on its best listing without viewing it', async () => {
		const { getByRole, onview } = await renderInbox();
		expect(getByRole('option', { selected: true })).toHaveTextContent('20 000 Kč');
		expect(onview).not.toHaveBeenCalled();
	});

	test('views a listing picked with a click', async () => {
		const { getAllByRole, onview, container } = await renderInbox();
		await fireEvent.click(getAllByRole('option')[1]);
		expect(onview).toHaveBeenCalledWith('b');
		expect(container.querySelector('.listing-detail__price')).toHaveTextContent('25 000 Kč');
	});

	test('keeps a picked listing in its section until another is picked', async () => {
		const { getAllByRole, prices } = await renderInbox();
		await fireEvent.click(getAllByRole('option')[1]);
		expect(prices('Nové')).toEqual(['20 000 Kč', '25 000 Kč']);
		await fireEvent.click(getAllByRole('option')[0]);
		expect(prices('Nové')).toEqual(['20 000 Kč']);
		expect(prices('Už zobrazené')).toEqual(['25 000 Kč', '30 000 Kč']);
	});

	test('moves and views with the arrow keys', async () => {
		const { listbox, onview, getByRole } = await renderInbox();
		await fireEvent.keyDown(listbox, { key: 'ArrowDown' });
		expect(onview).toHaveBeenCalledWith('b');
		expect(getByRole('option', { selected: true })).toHaveTextContent('25 000 Kč');
	});

	test('stars the picked listing with F, but leaves Ctrl+F to the browser', async () => {
		const { listbox, onfavourite } = await renderInbox();
		await fireEvent.keyDown(listbox, { key: 'f', ctrlKey: true });
		expect(onfavourite).not.toHaveBeenCalled();
		await fireEvent.keyDown(listbox, { key: 'f' });
		expect(onfavourite).toHaveBeenCalledWith('a', true);
	});

	test('keeps a listing starred from its details in its section while picked', async () => {
		const { getByRole, prices } = await renderInbox();
		await fireEvent.click(getByRole('button', { name: /Přidat do oblíbených/ }));
		expect(prices('Nové')).toEqual(['20 000 Kč', '25 000 Kč']);
	});

	test('opens the picked listing on its portal with Enter', async () => {
		const open = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
		const { listbox } = await renderInbox();
		await fireEvent.keyDown(listbox, { key: 'Enter' });
		expect(open).toHaveBeenCalledOnce();
		open.mockRestore();
	});

	test('says when a profile has no listings yet', async () => {
		const { getByText } = await renderWithTranslator(InboxHarness, {
			listings: [],
			preferences: null,
			onview: () => {},
			onfavourite: () => {}
		});
		expect(getByText('Zatím žádné inzeráty. Najde je scan.')).toBeInTheDocument();
	});
});
