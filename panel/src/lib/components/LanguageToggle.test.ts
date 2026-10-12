import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import type { Language } from '$lib/user-config';
import LanguageToggle from './LanguageToggle.svelte';

async function renderToggle(language: Language) {
	const onchange = vi.fn();
	const rendered = await renderWithTranslator(LanguageToggle, { language, onchange });
	return { onchange, ...rendered };
}

describe('LanguageToggle', () => {
	test('offers each language by its code, the chosen one pressed', async () => {
		const { getByRole } = await renderToggle('cs');
		expect(getByRole('group', { name: 'Jazyk' })).toBeInTheDocument();
		expect(getByRole('button', { name: 'CS' })).toHaveAttribute('aria-pressed', 'true');
		expect(getByRole('button', { name: 'EN' })).toHaveAttribute('aria-pressed', 'false');
	});

	test('names each language in its own language', async () => {
		const { getByRole } = await renderToggle('cs');
		expect(getByRole('button', { name: 'CS' })).toHaveAttribute('title', 'Čeština');
		expect(getByRole('button', { name: 'EN' })).toHaveAttribute('title', 'English');
	});

	test('changes to another language', async () => {
		const { getByRole, onchange } = await renderToggle('cs');
		await fireEvent.click(getByRole('button', { name: 'EN' }));
		expect(onchange).toHaveBeenCalledWith('en');
	});

	test('leaves the chosen language as it is', async () => {
		const { getByRole, onchange } = await renderToggle('cs');
		await fireEvent.click(getByRole('button', { name: 'CS' }));
		expect(onchange).not.toHaveBeenCalled();
	});

	test('gives each flag clip paths of its own', async () => {
		const { container } = await renderToggle('cs');
		const ids = [...container.querySelectorAll('clipPath')].map((clip) => clip.id);
		expect(new Set(ids).size).toBe(ids.length);
	});
});
