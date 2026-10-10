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

	test('keeps viewed listings in their section until the listings load again', async () => {
		const { getAllByRole, getByRole, prices } = await renderInbox();
		await fireEvent.click(getAllByRole('option')[1]);
		expect(prices('Nové')).toEqual(['20 000 Kč', '25 000 Kč']);
		await fireEvent.click(getByRole('button', { name: 'Označit vše jako zobrazené' }));
		expect(prices('Už zobrazené')).toEqual(['20 000 Kč', '25 000 Kč', '30 000 Kč']);
	});

	test('moves and views with the arrow keys', async () => {
		const { listbox, onview, getByRole } = await renderInbox();
		await fireEvent.keyDown(listbox, { key: 'ArrowDown' });
		expect(onview).toHaveBeenCalledWith('b');
		expect(getByRole('option', { selected: true })).toHaveTextContent('25 000 Kč');
	});

	test('moves with the arrow keys while the focus is outside the list', async () => {
		const { getByRole } = await renderInbox();
		await fireEvent.keyDown(document.body, { key: 'ArrowDown' });
		expect(getByRole('option', { selected: true })).toHaveTextContent('25 000 Kč');
	});

	test('leaves the keys to a text field and to a modal dialog', async () => {
		const { onview, onfavourite } = await renderInbox();
		const field = document.body.appendChild(document.createElement('input'));
		const dialog = document.body.appendChild(document.createElement('div'));
		dialog.setAttribute('aria-modal', 'true');
		const button = dialog.appendChild(document.createElement('button'));
		await fireEvent.keyDown(field, { key: 'ArrowDown' });
		await fireEvent.keyDown(field, { key: 'f' });
		await fireEvent.keyDown(button, { key: 'ArrowDown' });
		expect(onview).not.toHaveBeenCalled();
		expect(onfavourite).not.toHaveBeenCalled();
		field.remove();
		dialog.remove();
	});

	test('steps to the next and previous listing from the sides of the details', async () => {
		const { getByRole, onview } = await renderInbox();
		await fireEvent.click(getByRole('button', { name: 'Další inzerát' }));
		expect(onview).toHaveBeenCalledWith('b');
		expect(getByRole('option', { selected: true })).toHaveTextContent('25 000 Kč');
		await fireEvent.click(getByRole('button', { name: 'Předchozí inzerát' }));
		expect(getByRole('option', { selected: true })).toHaveTextContent('20 000 Kč');
	});

	test('offers no step past either end of the list', async () => {
		const { getAllByRole, queryByRole } = await renderInbox();
		expect(queryByRole('button', { name: 'Předchozí inzerát' })).toBeNull();
		await fireEvent.click(getAllByRole('option')[2]);
		expect(queryByRole('button', { name: 'Další inzerát' })).toBeNull();
		expect(queryByRole('button', { name: 'Předchozí inzerát' })).not.toBeNull();
	});

	test('stars the picked listing with F, but leaves Ctrl+F to the browser', async () => {
		const { listbox, onfavourite } = await renderInbox();
		await fireEvent.keyDown(listbox, { key: 'f', ctrlKey: true });
		expect(onfavourite).not.toHaveBeenCalled();
		await fireEvent.keyDown(listbox, { key: 'f' });
		expect(onfavourite).toHaveBeenCalledWith('a', true);
	});

	test('keeps a starred listing in its section after another is picked', async () => {
		const { getAllByRole, getByRole, prices } = await renderInbox();
		await fireEvent.click(getByRole('button', { name: /Přidat do oblíbených/ }));
		await fireEvent.click(getAllByRole('option')[1]);
		expect(prices('Nové')).toEqual(['20 000 Kč', '25 000 Kč']);
	});

	test('opens the picked listing on its portal with Enter', async () => {
		const open = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
		const { listbox } = await renderInbox();
		await fireEvent.keyDown(listbox, { key: 'Enter' });
		expect(open).toHaveBeenCalledOnce();
		open.mockRestore();
	});

	test('leaves Enter on a button to the button', async () => {
		const open = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
		const { getByRole } = await renderInbox();
		await fireEvent.keyDown(getByRole('button', { name: /Přidat do oblíbených/ }), { key: 'Enter' });
		expect(open).not.toHaveBeenCalled();
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
