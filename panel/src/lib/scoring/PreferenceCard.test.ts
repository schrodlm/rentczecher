import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import PreferenceCardHarness from '$lib/test-support/PreferenceCardHarness.svelte';

describe('PreferenceCard', () => {
	test('switches the preference with its switch', async () => {
		const ontoggle = vi.fn();
		const { getByRole } = await renderWithTranslator(PreferenceCardHarness, { on: false, ready: true, ontoggle });
		await fireEvent.click(getByRole('switch', { name: 'Preferovaná cena' }));
		expect(ontoggle).toHaveBeenCalledOnce();
	});

	test('shows its share while on', async () => {
		const { getByRole, getByText } = await renderWithTranslator(PreferenceCardHarness, {
			on: true,
			ready: true,
			ontoggle: () => {}
		});
		expect(getByRole('switch')).toBeChecked();
		expect(getByText('45 %')).toBeInTheDocument();
	});

	test('cannot be switched on until its preferred value is set', async () => {
		const { getByRole, queryByText } = await renderWithTranslator(PreferenceCardHarness, {
			on: false,
			ready: false,
			ontoggle: () => {}
		});
		expect(getByRole('switch')).toBeDisabled();
		expect(queryByText('45 %')).toBeNull();
	});

	test('shows its setting and its rule', async () => {
		const { getByText } = await renderWithTranslator(PreferenceCardHarness, { on: true, ready: true, ontoggle: () => {} });
		expect(getByText('nastavení')).toBeInTheDocument();
		expect(getByText('Plné body do 22 000 Kč.')).toBeInTheDocument();
	});
});
