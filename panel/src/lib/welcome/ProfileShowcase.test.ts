import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ProfileShowcase from './ProfileShowcase.svelte';

describe('ProfileShowcase', () => {
	test('opens on what a profile looks for', async () => {
		const { getByRole } = await renderWithTranslator(ProfileShowcase, {});
		expect(getByRole('heading', { name: 'Řekněte, co hledáte' })).toBeInTheDocument();
		expect(getByRole('button', { name: 'Předchozí' })).toBeDisabled();
	});

	test('steps through its slides with the arrows to the last', async () => {
		const { getByRole } = await renderWithTranslator(ProfileShowcase, {});
		const next = getByRole('button', { name: 'Další' });
		await fireEvent.click(next);
		expect(getByRole('heading', { name: 'Hlídá portály za vás' })).toBeInTheDocument();
		await fireEvent.click(next);
		expect(getByRole('heading', { name: 'Nejlepší byty nahoře' })).toBeInTheDocument();
		await fireEvent.click(next);
		expect(getByRole('heading', { name: 'Nic vám neuteče' })).toBeInTheDocument();
		expect(next).toBeDisabled();
	});

	test('jumps to a slide by its dot', async () => {
		const { getByRole } = await renderWithTranslator(ProfileShowcase, {});
		await fireEvent.click(getByRole('button', { name: 'Ukázka 3 z 4' }));
		expect(getByRole('heading', { name: 'Nejlepší byty nahoře' })).toBeInTheDocument();
	});
});
