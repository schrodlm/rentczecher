import { fireEvent, screen } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { ProfileModel } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import { storedProfile } from '$lib/test-support/stored-profile';
import ExportProfilesDialog from './ExportProfilesDialog.svelte';

const PROFILES = [storedProfile('p1', 'Praha'), storedProfile('p2', 'Brno')];

async function renderDialog(onexport: (chosen: ProfileModel[]) => Promise<boolean>) {
	const onclose = vi.fn();
	await renderWithTranslator(ExportProfilesDialog, { profiles: PROFILES, onexport, onclose });
	return { onclose };
}

describe('ExportProfilesDialog', () => {
	test('exports every profile unless one is unticked, and closes once saved', async () => {
		const onexport = vi.fn(async () => true);
		const { onclose } = await renderDialog(onexport);
		await fireEvent.click(screen.getByRole('checkbox', { name: 'Praha' }));
		await fireEvent.click(screen.getByRole('button', { name: 'Exportovat' }));
		expect(onexport).toHaveBeenCalledWith([PROFILES[1]]);
		expect(onclose).toHaveBeenCalledOnce();
	});

	test('cannot export with nothing ticked', async () => {
		await renderDialog(async () => true);
		await fireEvent.click(screen.getByRole('checkbox', { name: 'Praha' }));
		await fireEvent.click(screen.getByRole('checkbox', { name: 'Brno' }));
		expect(screen.getByRole('button', { name: 'Exportovat' })).toBeDisabled();
	});

	test('stays open when the save dialog is closed without saving', async () => {
		const { onclose } = await renderDialog(async () => false);
		await fireEvent.click(screen.getByRole('button', { name: 'Exportovat' }));
		expect(onclose).not.toHaveBeenCalled();
	});

	test('closes on Escape or a click beside it', async () => {
		const { onclose } = await renderDialog(async () => true);
		await fireEvent.keyDown(window, { key: 'Escape' });
		await fireEvent.click(document.querySelector('.export__backdrop')!);
		expect(onclose).toHaveBeenCalledTimes(2);
	});

	test('stays open while the save dialog is open', async () => {
		const { onclose } = await renderDialog(() => new Promise<boolean>(() => {}));
		await fireEvent.click(screen.getByRole('button', { name: 'Exportovat' }));
		expect(screen.getByRole('button', { name: 'Exportovat' })).toBeDisabled();
		await fireEvent.keyDown(window, { key: 'Escape' });
		await fireEvent.click(screen.getByRole('button', { name: 'Zrušit' }));
		expect(onclose).not.toHaveBeenCalled();
	});

	test('says why the file could not be saved, and stays open', async () => {
		const { onclose } = await renderDialog(async () => {
			throw new Error('disk full');
		});
		await fireEvent.click(screen.getByRole('button', { name: 'Exportovat' }));
		expect(screen.getByRole('status').textContent).toBe('Soubor se nepodařilo uložit: disk full');
		expect(onclose).not.toHaveBeenCalled();
	});
});
