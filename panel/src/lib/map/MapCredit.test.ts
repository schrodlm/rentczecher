import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import MapCredit from './MapCredit.svelte';

describe('MapCredit', () => {
	test("credits ČÚZK with the dataset's year, linking their terms", async () => {
		const { getByRole } = await renderWithTranslator(MapCredit, {});
		expect(getByRole('link', { name: 'ČÚZK, 2026' })).toHaveAttribute(
			'href',
			'https://cuzk.gov.cz/Predpisy/Podminky-poskytovani-prostor-dat-a-sitovych-sluzeb/Podminky-poskytovani-prostorovych-dat-CUZK.aspx'
		);
	});

	test('links the license', async () => {
		const { getByRole } = await renderWithTranslator(MapCredit, {});
		expect(getByRole('link', { name: 'CC BY 4.0' })).toHaveAttribute(
			'href',
			'https://creativecommons.org/licenses/by/4.0/'
		);
	});

	test('says the data was modified, and how', async () => {
		const { container } = await renderWithTranslator(MapCredit, {});
		expect(container.querySelector('.map-credit')).toHaveAttribute(
			'title',
			'Data míst z RÚIAN, upravená: zachovaná jména a středy míst, obrysy dopočtené ze středů'
		);
	});
});
