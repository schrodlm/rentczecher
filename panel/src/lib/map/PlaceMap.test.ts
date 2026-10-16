import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import { mapPointOf, OBVODY } from './czech-map';
import PlaceMap from './PlaceMap.svelte';

const unit = (code: number, name: string) => ({ code, name });

const IN_PRAHA_7 = {
	kraj: unit(19, 'Hlavní město Praha'),
	okres: null,
	obec: unit(554782, 'Praha'),
	obvod: unit(78, 'Praha 7'),
	mestska_cast: unit(500186, 'Praha 7'),
	cast_obce: null,
	ulice: null,
	cislo_popisne: null,
	cislo_orientacni: null
};

const IN_KDYNE = {
	kraj: unit(43, 'Plzeňský kraj'),
	okres: unit(3401, 'Domažlice'),
	obec: unit(553786, 'Kdyně'),
	obvod: null,
	mestska_cast: null,
	cast_obce: null,
	ulice: null,
	cislo_popisne: null,
	cislo_orientacni: null
};

describe('PlaceMap', () => {
	test('credits ČÚZK for the data it draws', async () => {
		const { getByRole } = await renderWithTranslator(PlaceMap, { location: IN_PRAHA_7, point: null });
		expect(getByRole('link', { name: 'ČÚZK, 2026' })).toBeInTheDocument();
		expect(getByRole('link', { name: 'CC BY 4.0' })).toBeInTheDocument();
	});

	test('highlights the Praha district a listing lies in', async () => {
		const { container } = await renderWithTranslator(PlaceMap, { location: IN_PRAHA_7, point: null });
		const praha7 = OBVODY.find((obvod) => obvod.code === 78);
		expect(container.querySelector('.place-map__area')?.getAttribute('d')).toBe(praha7?.path);
		expect(container.querySelector('.place-map__town')).toBeNull();
	});

	test('highlights the okres of a listing elsewhere and marks its town', async () => {
		const { container } = await renderWithTranslator(PlaceMap, { location: IN_KDYNE, point: null });
		expect(container.querySelector('.place-map__area')).not.toBeNull();
		expect(container.querySelector('.place-map__town')).not.toBeNull();
	});

	test('pins a listing at its point instead of marking its town', async () => {
		const { container } = await renderWithTranslator(PlaceMap, {
			location: IN_KDYNE,
			point: { lat: 49.3906, lon: 13.0724 }
		});
		const pin = container.querySelector('.place-map__pin');
		const [x, y] = mapPointOf(49.3906, 13.0724);
		expect(Number(pin?.getAttribute('cx'))).toBeCloseTo(x);
		expect(Number(pin?.getAttribute('cy'))).toBeCloseTo(y);
		expect(container.querySelector('.place-map__town')).toBeNull();
	});

	test('pins nothing for a listing without a point', async () => {
		const { container } = await renderWithTranslator(PlaceMap, { location: IN_PRAHA_7, point: null });
		expect(container.querySelector('.place-map__pin')).toBeNull();
	});

	test('names itself and offers no controls', async () => {
		const { container, getByRole } = await renderWithTranslator(PlaceMap, { location: IN_KDYNE, point: null });
		expect(getByRole('img', { name: 'Mapa, kde inzerát leží' })).toBeInTheDocument();
		expect(container.querySelectorAll('button')).toHaveLength(0);
	});
});
