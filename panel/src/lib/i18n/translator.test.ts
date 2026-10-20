import { beforeAll, describe, expect, test } from 'vitest';
import { Translator } from './translator';

const NBSP = ' ';

let cs: Translator;
let en: Translator;

beforeAll(async () => {
	cs = await Translator.load('cs');
	en = await Translator.load('en');
});

describe('Translator', () => {
	test('knows the language it speaks', () => {
		expect(cs.language).toBe('cs');
		expect(en.language).toBe('en');
	});

	test('writes a price with its thousands grouped the language way, kept on one line', () => {
		expect(cs.price(25000)).toBe(`25${NBSP}000${NBSP}Kč`);
		expect(en.price(25000)).toBe(`25,000${NBSP}Kč`);
		expect(cs.price(500)).toBe(`500${NBSP}Kč`);
	});

	test('writes an area the language way', () => {
		expect(cs.area(1200)).toBe(`1${NBSP}200${NBSP}m²`);
		expect(en.area(1200)).toBe(`1,200${NBSP}m²`);
	});

	test('writes a distance in metres to the ten under a kilometre and in kilometres to the tenth past it', () => {
		expect(cs.distance(447)).toBe(`450${NBSP}m`);
		expect(cs.distance(996)).toBe(`1${NBSP}km`);
		expect(cs.distance(1234)).toBe(`1,2${NBSP}km`);
		expect(en.distance(1234)).toBe(`1.2${NBSP}km`);
		expect(cs.distance(2000)).toBe(`2${NBSP}km`);
	});

	test('writes the price per square metre rounded, and none for no size', () => {
		expect(cs.pricePerM2(21000, 52)).toBe(`404${NBSP}Kč/m²`);
		expect(cs.perM2(403.8)).toBe(`404${NBSP}Kč/m²`);
		expect(cs.pricePerM2(21000, 0)).toBeNull();
		expect(cs.pricePerM2(21000, -5)).toBeNull();
	});

	test('writes a typed number for a slider box, and an empty box for no number', () => {
		expect(cs.typedNumber(1500000).replace(/\s/g, ' ')).toBe('1 500 000');
		expect(en.typedNumber(1500000)).toBe('1,500,000');
		expect(cs.typedNumber(null)).toBe('');
	});

	test('writes dates with the day before the month in both languages', () => {
		const iso = '2026-09-03T08:00:00Z';
		expect(cs.dayAndMonth(iso)).toBe('3. 9.');
		expect(en.dayAndMonth(iso)).toBe('03/09');
		expect(cs.date(iso)).toBe('3. 9. 2026');
		expect(en.date(iso)).toBe('03/09/2026');
	});
});
