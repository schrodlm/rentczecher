import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import type { Theme } from '$lib/user-config';
import ThemeToggle from './ThemeToggle.svelte';

async function renderToggle(theme: Theme) {
	const onchange = vi.fn();
	const rendered = await renderWithTranslator(ThemeToggle, { theme, onchange });
	return { onchange, ...rendered };
}

describe('ThemeToggle', () => {
	test('names the theme it shows', async () => {
		const { getByRole } = await renderToggle('dark');
		expect(getByRole('button', { name: 'Vzhled: Tmavý' })).toBeInTheDocument();
	});

	test('steps from following the system to light, to dark, and back', async () => {
		for (const [shown, next] of [
			['system', 'light'],
			['light', 'dark'],
			['dark', 'system']
		] as const) {
			const { getByRole, onchange, unmount } = await renderToggle(shown);
			await fireEvent.click(getByRole('button'));
			expect(onchange).toHaveBeenCalledWith(next);
			unmount();
		}
	});
});
