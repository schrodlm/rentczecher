import { fireEvent, screen } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ProfilesMenu from './ProfilesMenu.svelte';

async function openMenu(canExport: boolean) {
	const onimport = vi.fn();
	const onexport = vi.fn();
	await renderWithTranslator(ProfilesMenu, { canExport, onimport, onexport });
	await fireEvent.click(screen.getByRole('button', { name: 'Další akce s profily' }));
	return { onimport, onexport };
}

describe('ProfilesMenu', () => {
	test('imports from its menu, and closes it', async () => {
		const { onimport } = await openMenu(true);
		await fireEvent.click(screen.getByRole('menuitem', { name: 'Importovat profily...' }));
		expect(onimport).toHaveBeenCalledOnce();
		expect(screen.queryByRole('menu')).toBeNull();
	});

	test('exports from its menu, and closes it', async () => {
		const { onexport } = await openMenu(true);
		await fireEvent.click(screen.getByRole('menuitem', { name: 'Exportovat profily...' }));
		expect(onexport).toHaveBeenCalledOnce();
		expect(screen.queryByRole('menu')).toBeNull();
	});

	test('cannot export while there is no profile', async () => {
		await openMenu(false);
		expect(screen.getByRole('menuitem', { name: 'Exportovat profily...' })).toBeDisabled();
		expect(screen.getByRole('menuitem', { name: 'Importovat profily...' })).toBeEnabled();
	});

	test('closes on Escape', async () => {
		await openMenu(true);
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(screen.queryByRole('menu')).toBeNull();
	});

	test('closes on a click beside it', async () => {
		await openMenu(true);
		await fireEvent.click(document.body);
		expect(screen.queryByRole('menu')).toBeNull();
	});
});
