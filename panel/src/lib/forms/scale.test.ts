import { describe, expect, test } from 'vitest';
import { LAND_SCALE, parseTypedNumber, priceScale, RENT_SCALE, SALE_SCALE, Scale, SIZE_SCALE } from './scale';

describe('Scale', () => {
	const scale = new Scale([0, 10, 20, 50]);

	test('counts its positions from zero', () => {
		expect(scale.lastIndex).toBe(3);
		expect(scale.valueAt(2)).toBe(20);
	});

	test.each([
		[0, 0],
		[12, 1],
		[16, 2],
		[34, 2],
		[36, 3],
		[500, 3],
		[-5, 0]
	])('places %i at position %i, the nearest stop', (value, index) => {
		expect(scale.nearestIndex(value)).toBe(index);
	});

	test('places a value halfway between two stops on the lower one', () => {
		expect(scale.nearestIndex(15)).toBe(1);
	});
});

describe('the editor scales', () => {
	test.each([
		['rent', RENT_SCALE],
		['sale', SALE_SCALE],
		['size', SIZE_SCALE],
		['land', LAND_SCALE]
	])('%s starts at zero and only rises', (_name, scale) => {
		expect(scale.valueAt(0)).toBe(0);
		for (let index = 1; index <= scale.lastIndex; index++) {
			expect(scale.valueAt(index)).toBeGreaterThan(scale.valueAt(index - 1));
		}
	});

	test('a rent search slides through rents, a sale search through sale prices', () => {
		expect(priceScale('rent')).toBe(RENT_SCALE);
		expect(priceScale('sale')).toBe(SALE_SCALE);
	});
});

describe('parseTypedNumber', () => {
	test.each([
		['25000', 25000],
		['25 000', 25000],
		[' 1 500 000 ', 1500000],
		['0', 0]
	])('reads %j as %i', (text, number) => {
		expect(parseTypedNumber(text)).toBe(number);
	});

	test.each(['', '   ', 'abc', '12.5', '-3', '1e3'])('reads %j as no number', (text) => {
		expect(parseTypedNumber(text)).toBeNull();
	});
});
