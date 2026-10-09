import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import RangeSliderHarness from '$lib/test-support/RangeSliderHarness.svelte';
import { Scale } from './scale';

const SCALE = new Scale([0, 10000, 20000, 30000, 40000]);

async function renderSlider(low: number | null = null, high: number | null = null) {
	const rendered = await renderWithTranslator(RangeSliderHarness, { scale: SCALE, low, high });
	const [lowHandle, highHandle] = rendered.getAllByRole('slider');
	const [lowBox, highBox] = rendered.getAllByRole('textbox');
	const bounds = () => JSON.parse(rendered.getByTestId('bounds').textContent ?? 'null');
	return { lowHandle, highHandle, lowBox, highBox, bounds, ...rendered };
}

describe('RangeSlider', () => {
	test('has no bounds with both handles at the ends', async () => {
		const { lowHandle, highHandle, highBox } = await renderSlider();
		expect(lowHandle).toHaveValue('0');
		expect(highHandle).toHaveValue('4');
		expect(highBox).toHaveAttribute('placeholder', 'bez omezení');
	});

	test('sets a bound by sliding a handle', async () => {
		const { lowHandle, highHandle, bounds } = await renderSlider();
		await fireEvent.input(lowHandle, { target: { value: '1' } });
		await fireEvent.input(highHandle, { target: { value: '3' } });
		expect(bounds()).toEqual([10000, 30000]);
	});

	test('drops a bound when its handle goes back to the end', async () => {
		const { lowHandle, highHandle, bounds } = await renderSlider(10000, 30000);
		await fireEvent.input(lowHandle, { target: { value: '0' } });
		await fireEvent.input(highHandle, { target: { value: '4' } });
		expect(bounds()).toEqual([null, null]);
	});

	test('keeps the handles from crossing', async () => {
		const { lowHandle, bounds } = await renderSlider(null, 20000);
		await fireEvent.input(lowHandle, { target: { value: '3' } });
		expect(bounds()).toEqual([20000, 20000]);
	});

	test('keeps a typed bound as typed and moves its handle to the nearest position', async () => {
		const { lowBox, lowHandle, bounds } = await renderSlider();
		await fireEvent.change(lowBox, { target: { value: '12 500' } });
		expect(bounds()).toEqual([12500, null]);
		expect(lowHandle).toHaveValue('1');
	});

	test('drops a bound when its box is emptied', async () => {
		const { highBox, bounds } = await renderSlider(null, 30000);
		await fireEvent.change(highBox, { target: { value: '' } });
		expect(bounds()).toEqual([null, null]);
	});

	test('writes a bound with the thousands spaced', async () => {
		const { highBox } = await renderSlider(null, 30000);
		expect((highBox as HTMLInputElement).value.replace(/\s/g, ' ')).toBe('30 000');
	});

	test('names each handle and box for the range and its end', async () => {
		const { getAllByLabelText } = await renderSlider();
		expect(getAllByLabelText('Nájem od')).toHaveLength(2);
		expect(getAllByLabelText('Nájem do')).toHaveLength(2);
	});
});
