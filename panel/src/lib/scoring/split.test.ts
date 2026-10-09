import { describe, expect, test } from 'vitest';
import { moveDivider, settled, switchOff, switchOn } from './split';
import type { Weights } from './wishes';

function weights(set: Partial<Weights>): Weights {
	return { price: 0, size: 0, land: 0, layout: 0, place: 0, ...set };
}

function sum(of: Weights): number {
	return of.price + of.size + of.land + of.layout + of.place;
}

describe('moveDivider', () => {
	test('moves points from one neighbour to the other', () => {
		const moved = moveDivider(weights({ price: 50, size: 30, layout: 20 }), 'price', 'size', 10);
		expect(moved).toEqual(weights({ price: 60, size: 20, layout: 20 }));
	});

	test('leaves either neighbour at least five points', () => {
		const start = weights({ price: 50, size: 50 });
		expect(moveDivider(start, 'price', 'size', 80)).toEqual(weights({ price: 95, size: 5 }));
		expect(moveDivider(start, 'price', 'size', -80)).toEqual(weights({ price: 5, size: 95 }));
	});

	test('keeps whole points', () => {
		expect(moveDivider(weights({ price: 50, size: 50 }), 'price', 'size', 2.4)).toEqual(
			weights({ price: 52, size: 48 })
		);
	});
});

describe('switchOn', () => {
	test('gives the preference an equal share, taken from the others in proportion', () => {
		const on = switchOn(weights({ price: 60, size: 40 }), 'layout', ['price', 'size']);
		expect(on).toEqual(weights({ price: 40, size: 27, layout: 33 }));
	});

	test('never squeezes a preference below five points', () => {
		const on = switchOn(weights({ price: 90, size: 5, land: 5 }), 'layout', ['price', 'size', 'land']);
		expect(on).toEqual(weights({ price: 65, size: 5, land: 5, layout: 25 }));
	});

	test('gives the first preference everything', () => {
		expect(switchOn(weights({}), 'price', [])).toEqual(weights({ price: 100 }));
	});
});

describe('switchOff', () => {
	test('hands the share back to the others in proportion', () => {
		const off = switchOff(weights({ price: 50, size: 30, layout: 20 }), 'price', ['price', 'size', 'layout']);
		expect(off).toEqual(weights({ size: 60, layout: 40 }));
	});

	test('leaves nothing weighted when the last one goes', () => {
		expect(switchOff(weights({ price: 100 }), 'price', ['price'])).toEqual(weights({}));
	});
});

describe('settled', () => {
	test('drops a preference that stopped counting and grows the rest to fill its share', () => {
		expect(settled(weights({ price: 50, size: 30, layout: 20 }), ['size', 'layout'])).toEqual(
			weights({ size: 60, layout: 40 })
		);
	});

	test('always adds up to exactly 100, leftovers to the earlier preference', () => {
		const thirds = settled(weights({ price: 1, size: 1, layout: 1 }), ['price', 'size', 'layout']);
		expect(thirds).toEqual(weights({ price: 34, size: 33, layout: 33 }));
		const uneven = weights({ price: 7, size: 13, layout: 29, place: 3 });
		expect(sum(settled(uneven, ['price', 'size', 'layout', 'place']))).toBe(100);
	});

	test('shares equally between preferences that weigh nothing yet', () => {
		expect(settled(weights({}), ['price', 'size'])).toEqual(weights({ price: 50, size: 50 }));
	});
});
