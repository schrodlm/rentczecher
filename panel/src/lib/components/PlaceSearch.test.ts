import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { Translator } from '$lib/i18n/translator';
import { placeLabel } from '$lib/places';
import { renderWithTranslator } from '$lib/test-support/render';
import PlaceSearch from './PlaceSearch.svelte';

const HOLESOVICE_PRAHA: NamedPlace = { kind: 'cast_obce', code: 490067, name: 'Holešovice', obec: 'Praha', okres: null };
const HOLESOVICE_CHROUSTOVICE: NamedPlace = {
	kind: 'cast_obce',
	code: 41114,
	name: 'Holešovice',
	obec: 'Chroustovice',
	okres: 'Chrudim'
};

async function renderSearch(found: NamedPlace[] = [HOLESOVICE_PRAHA, HOLESOVICE_CHROUSTOVICE]) {
	const search = vi.fn(async () => found);
	const onpick = vi.fn();
	const rendered = await renderWithTranslator(PlaceSearch, { search, placeholder: 'Hledat místo', onpick });
	const input = rendered.getByRole('combobox');
	return { search, onpick, input, ...rendered };
}

async function type(input: HTMLElement, text: string): Promise<void> {
	await fireEvent.input(input, { target: { value: text } });
	// Let the search's answer land.
	await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('placeLabel', () => {
	test('names the place with its kind and what it lies in', async () => {
		const t = await Translator.load('cs');
		expect(placeLabel(HOLESOVICE_CHROUSTOVICE, t)).toBe('Holešovice (část obce, Chroustovice, Chrudim)');
		expect(placeLabel({ kind: 'kraj', code: 43, name: 'Plzeňský kraj', obec: null, okres: null }, t)).toBe(
			'Plzeňský kraj (kraj)'
		);
	});
});

describe('PlaceSearch', () => {
	test('asks for places only from two letters on', async () => {
		const { input, search } = await renderSearch();
		await type(input, 'h');
		expect(search).not.toHaveBeenCalled();
		await type(input, 'ho');
		expect(search).toHaveBeenCalledWith('ho');
	});

	test('lists what it found, told apart by what each lies in', async () => {
		const { input, getAllByRole } = await renderSearch();
		await type(input, 'holeš');
		expect(getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
			'Holešovice (část obce, Praha)',
			'Holešovice (část obce, Chroustovice, Chrudim)'
		]);
	});

	test('picks a place with a click and clears itself', async () => {
		const { input, getAllByRole, onpick } = await renderSearch();
		await type(input, 'holeš');
		await fireEvent.mouseDown(getAllByRole('option')[1]);
		expect(onpick).toHaveBeenCalledWith(HOLESOVICE_CHROUSTOVICE);
		expect(input).toHaveValue('');
	});

	test('picks the highlighted place with the arrow keys and Enter', async () => {
		const { input, onpick } = await renderSearch();
		await type(input, 'holeš');
		await fireEvent.keyDown(input, { key: 'ArrowDown' });
		await fireEvent.keyDown(input, { key: 'Enter' });
		expect(onpick).toHaveBeenCalledWith(HOLESOVICE_CHROUSTOVICE);
	});

	test('wraps the highlight around the ends of the list', async () => {
		const { input, onpick } = await renderSearch();
		await type(input, 'holeš');
		await fireEvent.keyDown(input, { key: 'ArrowUp' });
		await fireEvent.keyDown(input, { key: 'Enter' });
		expect(onpick).toHaveBeenCalledWith(HOLESOVICE_CHROUSTOVICE);
	});

	test('closes the list on Escape', async () => {
		const { input, queryAllByRole } = await renderSearch();
		await type(input, 'holeš');
		await fireEvent.keyDown(input, { key: 'Escape' });
		expect(queryAllByRole('option')).toEqual([]);
	});

	test('ignores an answer to a query the user has typed past', async () => {
		let answerFirst: (places: NamedPlace[]) => void = () => {};
		const search = vi
			.fn()
			.mockImplementationOnce(() => new Promise<NamedPlace[]>((resolve) => (answerFirst = resolve)))
			.mockImplementationOnce(async () => [HOLESOVICE_PRAHA]);
		const { getByRole, getAllByRole } = await renderWithTranslator(PlaceSearch, {
			search,
			placeholder: 'Hledat místo',
			onpick: () => {}
		});
		const input = getByRole('combobox');
		await fireEvent.input(input, { target: { value: 'ho' } });
		await type(input, 'holeš');
		answerFirst([HOLESOVICE_CHROUSTOVICE]);
		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(getAllByRole('option').map((option) => option.textContent?.trim())).toEqual([
			'Holešovice (část obce, Praha)'
		]);
	});
});
