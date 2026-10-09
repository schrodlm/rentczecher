import { describe, expect, test } from 'vitest';
import type { NamedPlace } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import type { Search } from './profile-draft.svelte';
import SearchSummary from './SearchSummary.svelte';

const PRAHA_7: NamedPlace = { kind: 'mestska_cast', code: 500186, name: 'Praha 7', obec: 'Praha', okres: null };

const FLAT: Search = {
	offer_type: 'rent',
	estate_type: 'flat',
	min_price: 15000,
	max_price: 30000,
	min_size_m2: 40,
	max_size_m2: null,
	min_land_m2: 500,
	dispositions: ['2+kk', 'atypicky']
};

async function facts(search: Search): Promise<string> {
	const { container } = await renderWithTranslator(SearchSummary, { search, place: PRAHA_7 });
	const text = container.querySelector('.search-summary__facts')?.textContent ?? '';
	return text.replace(/\s*·\s*/g, ' · ').replace(/\s+/g, ' ').trim();
}

describe('SearchSummary', () => {
	test('lists the search as one line of facts', async () => {
		expect(await facts(FLAT)).toBe(
			'Pronájem bytu · Praha 7 (městská část, Praha) · 15 000 Kč až 30 000 Kč · od 40 m² · 2+kk, atypická'
		);
	});

	test('names a bound with only its one end', async () => {
		expect(await facts({ ...FLAT, min_price: null, min_size_m2: null, max_size_m2: 90, dispositions: [] })).toBe(
			'Pronájem bytu · Praha 7 (městská část, Praha) · do 30 000 Kč · do 90 m²'
		);
	});

	test('gives land its land and no size or layouts', async () => {
		expect(await facts({ ...FLAT, offer_type: 'sale', estate_type: 'land', min_price: null, max_price: null })).toBe(
			'Koupě pozemku · Praha 7 (městská část, Praha) · pozemek od 500 m²'
		);
	});

	test('says why the search cannot change', async () => {
		const { getByText } = await renderWithTranslator(SearchSummary, { search: FLAT, place: PRAHA_7 });
		expect(getByText(/Pro jiné hledání vytvořte nový profil/)).toBeInTheDocument();
	});
});
