import { fireEvent } from '@testing-library/svelte';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import type { Theme } from '$lib/user-config';
import WelcomeWizard from './WelcomeWizard.svelte';

const replaced = vi.hoisted(() => ({ urls: [] as string[] }));

vi.stubGlobal('location', { ...window.location, replace: (url: string) => replaced.urls.push(url) });

afterEach(() => {
	replaced.urls = [];
	delete document.documentElement.dataset.theme;
});

async function renderWizard(theme: Theme = 'system') {
	const oncomplete = vi.fn();
	const rendered = await renderWithTranslator(WelcomeWizard, { theme, oncomplete });
	const press = (name: string) => fireEvent.click(rendered.getByRole('button', { name }));
	return { oncomplete, press, ...rendered };
}

describe('WelcomeWizard', () => {
	test('opens on the language, the language it speaks picked', async () => {
		const { getByRole } = await renderWizard();
		expect(getByRole('dialog', { name: 'Vítejte v rentczecheru' })).toBeInTheDocument();
		expect(getByRole('button', { name: 'Čeština' })).toHaveAttribute('aria-pressed', 'true');
		expect(getByRole('img', { name: 'Krok 1 z 3' })).toBeInTheDocument();
	});

	test('reloads in another language, keeping the theme picked so far', async () => {
		const { press } = await renderWizard('dark');
		await press('English');
		expect(replaced.urls).toEqual(['?language=en&theme=dark']);
	});

	test('stays put when the language it speaks is picked', async () => {
		const { press } = await renderWizard();
		await press('Čeština');
		expect(replaced.urls).toEqual([]);
	});

	test('shows a picked theme at once', async () => {
		const { press, getByRole } = await renderWizard();
		await press('Pokračovat');
		await press('Tmavý');
		expect(document.documentElement.dataset.theme).toBe('dark');
		expect(getByRole('button', { name: 'Tmavý' })).toHaveAttribute('aria-pressed', 'true');
	});

	test('steps back to the language', async () => {
		const { press, getByRole } = await renderWizard();
		await press('Pokračovat');
		await press('← Zpět');
		expect(getByRole('button', { name: 'English' })).toBeInTheDocument();
	});

	test('finishes with the choices made, creating a profile', async () => {
		const { press, oncomplete } = await renderWizard();
		await press('Pokračovat');
		await press('Tmavý');
		await press('Pokračovat');
		await press('Vytvořit profil');
		expect(oncomplete).toHaveBeenCalledWith({ theme: 'dark', language: 'cs' }, true);
	});

	test('finishes leaving the profile for later', async () => {
		const { press, oncomplete } = await renderWizard('light');
		await press('Pokračovat');
		await press('Pokračovat');
		await press('Později');
		expect(oncomplete).toHaveBeenCalledWith({ theme: 'light', language: 'cs' }, false);
	});
});
