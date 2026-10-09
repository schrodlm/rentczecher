import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import SortMenuHarness from '$lib/test-support/SortMenuHarness.svelte';

async function renderMenu() {
	const rendered = await renderWithTranslator(SortMenuHarness, { order: { field: 'score', descending: true } });
	const order = () => JSON.parse(rendered.getByTestId('order').textContent ?? '');
	return { order, ...rendered };
}

describe('SortMenu', () => {
	test('picks a field in its natural direction', async () => {
		const { getByRole, order } = await renderMenu();
		await fireEvent.click(getByRole('button', { name: 'Řadit podle: Skóre' }));
		await fireEvent.click(getByRole('menuitemradio', { name: 'Cena' }));
		expect(order()).toEqual({ field: 'price', descending: false });
	});

	test('turns the order around with its arrow', async () => {
		const { getByRole, order } = await renderMenu();
		await fireEvent.click(getByRole('button', { name: 'Sestupně' }));
		expect(order()).toEqual({ field: 'score', descending: false });
		expect(getByRole('button', { name: 'Vzestupně' })).toBeInTheDocument();
	});

	test('ticks the field the listings are sorted by', async () => {
		const { getByRole } = await renderMenu();
		await fireEvent.click(getByRole('button', { name: 'Řadit podle: Skóre' }));
		expect(getByRole('menuitemradio', { name: 'Skóre' })).toHaveAttribute('aria-checked', 'true');
	});

	test('closes on Escape without letting it reach a window around', async () => {
		const { getByRole, queryByRole } = await renderMenu();
		await fireEvent.click(getByRole('button', { name: 'Řadit podle: Skóre' }));
		const escape = new KeyboardEvent('keydown', { key: 'Escape', cancelable: true, bubbles: true });
		window.dispatchEvent(escape);
		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(escape.defaultPrevented).toBe(true);
		expect(queryByRole('menu')).toBeNull();
	});
});
