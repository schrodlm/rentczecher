import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ValueSliderHarness from '$lib/test-support/ValueSliderHarness.svelte';
import { Scale } from './scale';

const SCALE = new Scale([0, 40, 60, 80, 100]);

async function renderSlider(value: number | null = null) {
	const rendered = await renderWithTranslator(ValueSliderHarness, { scale: SCALE, value });
	const handle = rendered.getByRole('slider');
	const box = rendered.getByRole('textbox');
	const shown = () => JSON.parse(rendered.getByTestId('value').textContent ?? 'null');
	return { handle, box, shown, ...rendered };
}

describe('ValueSlider', () => {
	test('has no value with its handle at the start', async () => {
		const { handle, box } = await renderSlider();
		expect(handle).toHaveValue('0');
		expect(box).toHaveValue('');
		expect(box).toHaveAttribute('placeholder', 'ideální velikost');
	});

	test('sets the value by sliding', async () => {
		const { handle, shown } = await renderSlider();
		await fireEvent.input(handle, { target: { value: '3' } });
		expect(shown()).toBe(80);
	});

	test('drops the value when the handle goes back to the start', async () => {
		const { handle, shown } = await renderSlider(60);
		await fireEvent.input(handle, { target: { value: '0' } });
		expect(shown()).toBeNull();
	});

	test('keeps a typed value as typed and moves the handle to the nearest position', async () => {
		const { handle, box, shown } = await renderSlider();
		await fireEvent.change(box, { target: { value: '72' } });
		expect(shown()).toBe(72);
		expect(handle).toHaveValue('3');
	});

	test('drops the value when the box is emptied', async () => {
		const { box, shown } = await renderSlider(60);
		await fireEvent.change(box, { target: { value: '' } });
		expect(shown()).toBeNull();
	});

	test('names its handle and box', async () => {
		const { getAllByLabelText } = await renderSlider();
		expect(getAllByLabelText('Ideální velikost')).toHaveLength(2);
	});
});
