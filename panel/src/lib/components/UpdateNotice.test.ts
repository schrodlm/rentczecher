import { fireEvent, screen } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { UpdateState, UpdateStore } from '$lib/stores/update.svelte';
import { renderWithTranslator } from '$lib/test-support/render';
import UpdateNotice from './UpdateNotice.svelte';

function store(state: UpdateState): UpdateStore {
	return { state, install: vi.fn() } as unknown as UpdateStore;
}

describe('UpdateNotice', () => {
	test('shows nothing while the app is up to date', async () => {
		const { container } = await renderWithTranslator(UpdateNotice, { updates: store({ status: 'none' }) });
		expect(container.textContent?.trim()).toBe('');
	});

	test('offers to install an available version', async () => {
		const updates = store({ status: 'available', version: '0.3.0' });
		await renderWithTranslator(UpdateNotice, { updates });
		expect(screen.getByText('Je k dispozici verze 0.3.0')).toBeTruthy();
		await fireEvent.click(screen.getByRole('button', { name: 'Aktualizovat a restartovat' }));
		expect(updates.install).toHaveBeenCalledOnce();
	});

	test('shows how far the download has come', async () => {
		await renderWithTranslator(UpdateNotice, {
			updates: store({ status: 'installing', version: '0.3.0', percent: 40 })
		});
		expect(screen.getByRole('status').textContent?.trim()).toBe('Stahuji aktualizaci... 40 %');
	});

	test('says it is downloading while the size is unknown', async () => {
		await renderWithTranslator(UpdateNotice, {
			updates: store({ status: 'installing', version: '0.3.0', percent: null })
		});
		expect(screen.getByRole('status').textContent?.trim()).toBe('Stahuji aktualizaci...');
	});

	test('links a failed install to the release to download by hand', async () => {
		await renderWithTranslator(UpdateNotice, {
			updates: store({ status: 'failed', version: '0.3.0', error: 'pkexec was dismissed' })
		});
		const link = screen.getByRole('link', { name: 'Stáhnout ručně' }) as HTMLAnchorElement;
		expect(link.href).toBe('https://github.com/schrodlm/rentczecher/releases/tag/v0.3.0');
		expect(screen.getByRole('alert').title).toBe('pkexec was dismissed');
	});
});
