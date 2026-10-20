import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import StreetMap from './StreetMap.svelte';
import StreetMapCredit from './StreetMapCredit.svelte';
import StreetMapWindow from './StreetMapWindow.svelte';

describe('StreetMap', () => {
	test('shows the point on OpenStreetMap tiles', async () => {
		const { container } = await renderWithTranslator(StreetMap, { point: { lat: 50.1, lon: 14.44 }, wholeWindow: false });
		const tiles = [...container.querySelectorAll<HTMLImageElement>('img.leaflet-tile')];
		expect(tiles.length).toBeGreaterThan(0);
		expect(tiles.every((tile) => tile.src.startsWith('https://tile.openstreetmap.org/15/'))).toBe(true);
	});

	test('pins the point', async () => {
		const { container } = await renderWithTranslator(StreetMap, { point: { lat: 50.1, lon: 14.44 }, wholeWindow: false });
		expect(container.querySelectorAll('.street-map__pin')).toHaveLength(1);
	});

	test("leaves out Leaflet's own attribution badge", async () => {
		const { container } = await renderWithTranslator(StreetMap, { point: { lat: 50.1, lon: 14.44 }, wholeWindow: false });
		expect(container.querySelector('.leaflet-control-attribution')).toBeNull();
	});

	test('moves to a new point while it stays shown', async () => {
		const { container, rerender } = await renderWithTranslator(StreetMap, { point: { lat: 50.1, lon: 14.44 }, wholeWindow: false });
		const tiles = () => [...container.querySelectorAll<HTMLImageElement>('img.leaflet-tile')].map((tile) => tile.src);
		const before = tiles();
		await rerender({ point: { lat: 49.2, lon: 16.6 }, wholeWindow: false });
		expect(tiles().some((tile) => !before.includes(tile))).toBe(true);
	});
});

describe('StreetMapCredit', () => {
	test('credits the OpenStreetMap contributors and links their terms', async () => {
		const { getByText } = await renderWithTranslator(StreetMapCredit, {});
		expect(getByText('© přispěvatelé OpenStreetMap')).toHaveAttribute('href', 'https://www.openstreetmap.org/copyright');
	});
});

describe('StreetMapWindow', () => {
	test('shows the map over the whole window, credited', async () => {
		const { getByRole } = await renderWithTranslator(StreetMapWindow, { point: { lat: 50.1, lon: 14.44 }, onclose: () => {} });
		const window_ = getByRole('dialog');
		expect(window_).toHaveAttribute('aria-modal', 'true');
		expect(window_.querySelector('.street-map')).not.toBeNull();
		expect(getByRole('link', { name: '© přispěvatelé OpenStreetMap' })).toBeInTheDocument();
	});

	test('closes with Escape and with its button', async () => {
		const onclose = vi.fn();
		const { getByLabelText } = await renderWithTranslator(StreetMapWindow, { point: { lat: 50.1, lon: 14.44 }, onclose });
		await fireEvent.keyDown(window, { key: 'Escape' });
		await fireEvent.click(getByLabelText('Zavřít'));
		expect(onclose).toHaveBeenCalledTimes(2);
	});
});
