import { fireEvent } from '@testing-library/svelte';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import SplitBarHarness from '$lib/test-support/SplitBarHarness.svelte';
import type { Weights } from './preferences';

const WEIGHTS: Weights = { price: 50, size: 30, land: 0, layout: 20, place: 0 };

async function renderBar() {
	const rendered = await renderWithTranslator(SplitBarHarness, {
		weights: { ...WEIGHTS },
		counting: ['price', 'size', 'layout']
	});
	const weights = (): Weights => JSON.parse(rendered.getByTestId('weights').textContent ?? '');
	return { weights, ...rendered };
}

beforeEach(() => {
	// jsdom lays nothing out and captures no pointer.
	HTMLElement.prototype.setPointerCapture = vi.fn();
	vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ width: 500 } as DOMRect);
});

describe('SplitBar', () => {
	test('shows each counting preference with its share', async () => {
		const { container } = await renderBar();
		const segments = [...container.querySelectorAll('.split-bar__segment')].map((segment) =>
			(segment.textContent ?? '').replace(/\s+/g, ' ').trim()
		);
		expect(segments).toEqual(['Cena 50 %', 'Velikost 30 %', 'Dispozice 20 %']);
	});

	test('puts a divider between each pair of neighbours', async () => {
		const { getAllByRole } = await renderBar();
		expect(getAllByRole('slider').map((divider) => divider.getAttribute('aria-label'))).toEqual([
			'Předěl: Cena a Velikost',
			'Předěl: Velikost a Dispozice'
		]);
	});

	test('moves weight between neighbours as a divider is dragged', async () => {
		const { getAllByRole, weights } = await renderBar();
		const divider = getAllByRole('slider')[0];
		await fireEvent.pointerDown(divider, { pointerId: 1, clientX: 100 });
		await fireEvent.pointerMove(divider, { pointerId: 1, clientX: 150 });
		expect(weights()).toMatchObject({ price: 60, size: 20, layout: 20 });
		await fireEvent.pointerUp(divider, { pointerId: 1, clientX: 150 });
		await fireEvent.pointerMove(divider, { pointerId: 1, clientX: 300 });
		expect(weights()).toMatchObject({ price: 60, size: 20 });
	});

	test('nudges a divider with the arrow keys, by five with shift', async () => {
		const { getAllByRole, weights } = await renderBar();
		const divider = getAllByRole('slider')[1];
		await fireEvent.keyDown(divider, { key: 'ArrowRight' });
		expect(weights()).toMatchObject({ size: 31, layout: 19 });
		await fireEvent.keyDown(divider, { key: 'ArrowLeft', shiftKey: true });
		expect(weights()).toMatchObject({ size: 26, layout: 24 });
	});
});
