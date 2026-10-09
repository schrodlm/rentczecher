import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import PreferenceCardHarness from '$lib/test-support/PreferenceCardHarness.svelte';

describe('PreferenceCard', () => {
	test('shows its share while it counts', async () => {
		const { getByText, container } = await renderWithTranslator(PreferenceCardHarness, { share: 45 });
		expect(getByText('45 %')).toBeInTheDocument();
		expect(container.querySelector('.preference-card--off')).toBeNull();
	});

	test('looks muted and shows no share until its preferred value is set', async () => {
		const { queryByText, container } = await renderWithTranslator(PreferenceCardHarness, { share: null });
		expect(queryByText('%', { exact: false })).toBeNull();
		expect(container.querySelector('.preference-card--off')).not.toBeNull();
	});

	test('shows its setting and its rule', async () => {
		const { getByText } = await renderWithTranslator(PreferenceCardHarness, { share: 45 });
		expect(getByText('nastavení')).toBeInTheDocument();
		expect(getByText('Plné body do 22 000 Kč.')).toBeInTheDocument();
	});
});
