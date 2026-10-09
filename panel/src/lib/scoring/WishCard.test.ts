import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import WishCardHarness from '$lib/test-support/WishCardHarness.svelte';

describe('WishCard', () => {
	test('sets how much the wish matters', async () => {
		const { getByRole, getByTestId } = await renderWithTranslator(WishCardHarness, { importance: 0, ready: true });
		await fireEvent.click(getByRole('radio', { name: 'Nejvíc' }));
		expect(getByTestId('importance')).toHaveTextContent('4');
		expect(getByRole('radio', { name: 'Nejvíc' })).toBeChecked();
	});

	test('can only be off until its setting is chosen', async () => {
		const { getAllByRole } = await renderWithTranslator(WishCardHarness, { importance: 0, ready: false });
		const levels = getAllByRole('radio');
		expect(levels.filter((level) => !(level as HTMLButtonElement).disabled).map((level) => level.textContent)).toEqual([
			'Vypnuto'
		]);
	});

	test('shows its setting and its rule', async () => {
		const { getByText } = await renderWithTranslator(WishCardHarness, { importance: 2, ready: true });
		expect(getByText('nastavení')).toBeInTheDocument();
		expect(getByText('Plné body do 22 000 Kč.')).toBeInTheDocument();
	});

	test('names what its importance is for', async () => {
		const { getByRole } = await renderWithTranslator(WishCardHarness, { importance: 0, ready: true });
		expect(getByRole('radiogroup', { name: 'Jak moc záleží na: Dobrá cena' })).toBeInTheDocument();
	});
});
