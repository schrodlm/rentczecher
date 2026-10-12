import { fireEvent } from '@testing-library/svelte';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import type { Theme } from '$lib/user-config';
import ThemeToggle from './ThemeToggle.svelte';

const systemMatchMedia = window.matchMedia;

afterEach(() => {
	window.matchMedia = systemMatchMedia;
});

function onADarkSystem(): void {
	window.matchMedia = (query: string) =>
		({ ...systemMatchMedia(query), matches: query === '(prefers-color-scheme: dark)' }) as MediaQueryList;
}

async function renderToggle(theme: Theme) {
	const onchange = vi.fn();
	const rendered = await renderWithTranslator(ThemeToggle, { theme, onchange });
	return { onchange, button: rendered.getByRole('button'), ...rendered };
}

describe('ThemeToggle', () => {
	test('names the chosen theme and turns it to the other one', async () => {
		const dark = await renderToggle('dark');
		expect(dark.button).toHaveAccessibleName('Vzhled: Tmavý');
		await fireEvent.click(dark.button);
		expect(dark.onchange).toHaveBeenCalledWith('light');
		dark.unmount();

		const light = await renderToggle('light');
		expect(light.button).toHaveAccessibleName('Vzhled: Světlý');
		await fireEvent.click(light.button);
		expect(light.onchange).toHaveBeenCalledWith('dark');
	});

	test('shows a light system as light, turning it dark', async () => {
		const { button, onchange } = await renderToggle('system');
		expect(button).toHaveAccessibleName('Vzhled: Světlý');
		await fireEvent.click(button);
		expect(onchange).toHaveBeenCalledWith('dark');
	});

	test('shows a dark system as dark, turning it light', async () => {
		onADarkSystem();
		const { button, onchange } = await renderToggle('system');
		expect(button).toHaveAccessibleName('Vzhled: Tmavý');
		await fireEvent.click(button);
		expect(onchange).toHaveBeenCalledWith('light');
	});
});
