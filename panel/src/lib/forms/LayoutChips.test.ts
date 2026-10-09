import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import { Translator } from '$lib/i18n/translator';
import { LAYOUTS, layoutName, layoutsByRooms, type Layout } from '$lib/layouts';
import { renderWithTranslator } from '$lib/test-support/render';
import LayoutChipsHarness from '$lib/test-support/LayoutChipsHarness.svelte';

async function renderChips(selected: Layout[] = []) {
	const rendered = await renderWithTranslator(LayoutChipsHarness, { selected });
	const picked = () => JSON.parse(rendered.getByTestId('selected').textContent ?? '[]');
	return { picked, ...rendered };
}

describe('layouts', () => {
	test('groups each room count’s two layouts and leaves atypical alone', () => {
		const groups = layoutsByRooms();
		expect(groups).toHaveLength(10);
		expect(groups[1]).toEqual(['2+kk', '2+1']);
		expect(groups.at(-1)).toEqual(['atypicky']);
		expect(groups.flat()).toEqual(LAYOUTS);
	});

	test('names atypical in words and the rest by their code', async () => {
		const t = await Translator.load('cs');
		expect(layoutName('atypicky', t)).toBe('atypická');
		expect(layoutName('3+kk', t)).toBe('3+kk');
	});
});

describe('LayoutChips', () => {
	test('offers every layout, none picked', async () => {
		const { getAllByRole } = await renderChips();
		const chips = getAllByRole('button');
		expect(chips).toHaveLength(19);
		expect(chips.every((chip) => chip.getAttribute('aria-pressed') === 'false')).toBe(true);
	});

	test('picks a layout and drops it again', async () => {
		const { getByRole, picked } = await renderChips();
		await fireEvent.click(getByRole('button', { name: '2+kk' }));
		await fireEvent.click(getByRole('button', { name: 'atypická' }));
		expect(picked()).toEqual(['2+kk', 'atypicky']);
		await fireEvent.click(getByRole('button', { name: '2+kk' }));
		expect(picked()).toEqual(['atypicky']);
	});

	test('shows the picked layouts as pressed', async () => {
		const { getByRole } = await renderChips(['3+1']);
		expect(getByRole('button', { name: '3+1' })).toHaveAttribute('aria-pressed', 'true');
		expect(getByRole('button', { name: '3+kk' })).toHaveAttribute('aria-pressed', 'false');
	});

	test('names the group for screen readers', async () => {
		const { getByRole } = await renderChips();
		expect(getByRole('group', { name: 'Dispozice' })).toBeInTheDocument();
	});
});
