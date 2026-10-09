import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { ApiError, type NamedPlace, type ProfileModel } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import { ProfileDraft } from './profile-draft.svelte';
import ProfileEditor from './ProfileEditor.svelte';

const PRAHA: NamedPlace = { kind: 'obec', code: 554782, name: 'Praha', obec: null, okres: null };

const STORED: ProfileModel = {
	id: 'p1',
	name: 'Praha byty',
	paused_at: null,
	portals: ['sreality'],
	criteria: {
		offer_type: 'rent',
		estate_type: 'flat',
		place: PRAHA,
		min_price: null,
		max_price: 30000,
		min_size_m2: null,
		max_size_m2: null,
		min_land_m2: null,
		dispositions: []
	},
	preferences: {
		price_per_m2_weight: 0,
		disposition_weight: 0,
		preferred_dispositions: [],
		size_weight: 0,
		preferred_size_m2: null,
		place_weight: 0,
		preferred_places: [],
		land_weight: 0,
		preferred_land_m2: null,
		price_weight: 0,
		preferred_price: null
	}
};

async function renderEditor(draft: ProfileDraft, stored: boolean, onsave = vi.fn(async () => {})) {
	const ondelete = vi.fn(async () => {});
	const oncancel = vi.fn();
	const rendered = await renderWithTranslator(ProfileEditor, {
		draft,
		stored,
		searchPlaces: async () => [],
		onsave,
		ondelete,
		oncancel
	});
	return { onsave, ondelete, oncancel, ...rendered };
}

function placedBlank(): ProfileDraft {
	const draft = ProfileDraft.blank();
	draft.setPlace(PRAHA);
	return draft;
}

describe('ProfileEditor', () => {
	test('creates a profile once it is named', async () => {
		const { getByRole, getByPlaceholderText, getByText, onsave } = await renderEditor(placedBlank(), false);
		const create = getByRole('button', { name: 'Vytvořit profil' });
		expect(create).toBeDisabled();
		expect(getByText('Pojmenujte profil.')).toBeInTheDocument();
		await fireEvent.input(getByPlaceholderText('např. Byty Praha 7'), { target: { value: 'Byty' } });
		expect(create).toBeEnabled();
		await fireEvent.click(create);
		expect(onsave).toHaveBeenCalledOnce();
	});

	test('says when a typed lowest price is above the highest', async () => {
		const draft = placedBlank();
		draft.search = { ...draft.search, min_price: 30000, max_price: 20000 };
		const { getByText } = await renderEditor(draft, false);
		expect(getByText('Nejnižší cena je vyšší než nejvyšší.')).toBeInTheDocument();
	});

	test('shows why a save failed, with the reason the engine gave', async () => {
		const draft = placedBlank();
		draft.name = 'Byty';
		const refused = new ApiError(new Response(null, { status: 422 }), 'min_price must not exceed max_price');
		const { getByRole, findByText } = await renderEditor(draft, false, vi.fn(async () => Promise.reject(refused)));
		await fireEvent.click(getByRole('button', { name: 'Vytvořit profil' }));
		expect(await findByText('Profil se nepodařilo uložit: min_price must not exceed max_price')).toBeInTheDocument();
	});

	test('shows a stored profile its fixed search, not the search controls', async () => {
		const { getByText, queryByText } = await renderEditor(ProfileDraft.of(STORED), true);
		expect(getByText('Upravit profil')).toBeInTheDocument();
		expect(getByText('Pronájem bytu')).toBeInTheDocument();
		expect(queryByText('Kde?')).toBeNull();
	});

	test('pauses a stored profile', async () => {
		const draft = ProfileDraft.of(STORED);
		const { getByRole } = await renderEditor(draft, true);
		await fireEvent.click(getByRole('checkbox', { name: 'Sleduje se' }));
		expect(draft.paused).toBe(true);
	});

	test('asks before deleting a profile', async () => {
		const { getByRole, ondelete } = await renderEditor(ProfileDraft.of(STORED), true);
		await fireEvent.click(getByRole('button', { name: 'Smazat profil' }));
		expect(ondelete).not.toHaveBeenCalled();
		await fireEvent.click(getByRole('button', { name: 'Smazat' }));
		expect(ondelete).toHaveBeenCalledOnce();
	});

	test('backs out of the delete question on Escape, and closes on the next', async () => {
		const { getByRole, queryByRole, oncancel } = await renderEditor(ProfileDraft.of(STORED), true);
		await fireEvent.click(getByRole('button', { name: 'Smazat profil' }));
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(queryByRole('button', { name: 'Smazat' })).toBeNull();
		expect(oncancel).not.toHaveBeenCalled();
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(oncancel).toHaveBeenCalledOnce();
	});

	test('stays open while a save is running', async () => {
		const draft = placedBlank();
		draft.name = 'Byty';
		const { getByRole, oncancel } = await renderEditor(draft, false, vi.fn(() => new Promise<void>(() => {})));
		await fireEvent.click(getByRole('button', { name: 'Vytvořit profil' }));
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(oncancel).not.toHaveBeenCalled();
	});
});
