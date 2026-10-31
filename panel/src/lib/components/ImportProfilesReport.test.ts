import { screen } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { ImportReport } from '$lib/import-profiles';
import { renderWithTranslator } from '$lib/test-support/render';
import { storedProfile } from '$lib/test-support/stored-profile';
import ImportProfilesReport from './ImportProfilesReport.svelte';

function renderReport(report: ImportReport) {
	return renderWithTranslator(ImportProfilesReport, { report, onclose: vi.fn() });
}

describe('ImportProfilesReport', () => {
	test('names the profiles it added', async () => {
		await renderReport({
			status: 'done',
			outcome: { added: [storedProfile('n1', 'Praha'), storedProfile('n2', 'Brno (2)')], refused: [] }
		});
		expect(screen.getByText('Přidány 2 profily:')).toBeTruthy();
		expect(screen.getByText('Brno (2)')).toBeTruthy();
		expect(screen.queryByRole('alert')).toBeNull();
	});

	test('names each refused profile, with the reason on hover', async () => {
		await renderReport({
			status: 'done',
			outcome: { added: [storedProfile('n1', 'Praha')], refused: [{ name: 'Brno', reason: 'place obec 1 not found' }] }
		});
		expect(screen.getByRole('alert').textContent).toBe('1 profil se nepodařilo přidat:');
		expect(screen.getByText('Brno').getAttribute('title')).toBe('place obec 1 not found');
	});

	test('says when the file holds no profiles', async () => {
		await renderReport({ status: 'done', outcome: { added: [], refused: [] } });
		expect(screen.getByText('Soubor neobsahuje žádné profily.')).toBeTruthy();
	});

	test('says when the file is not a file of profiles', async () => {
		await renderReport({ status: 'unreadable' });
		expect(screen.getByRole('alert').textContent).toBe('Tento soubor neobsahuje profily, které rentczecher umí přečíst.');
	});

	test('says why the file could not be read', async () => {
		await renderReport({ status: 'failed', reason: 'permission denied' });
		expect(screen.getByRole('alert').textContent).toBe('Soubor se nepodařilo přečíst: permission denied');
	});
});
