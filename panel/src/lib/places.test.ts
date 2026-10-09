import { describe, expect, test } from 'vitest';
import { kindsInside } from './places';

describe('kindsInside', () => {
	test('offers every finer kind, even those that only partly lie inside', () => {
		expect(kindsInside('mestska_cast')).toEqual(['cast_obce', 'ulice']);
	});

	test('offers nothing inside a street', () => {
		expect(kindsInside('ulice')).toEqual([]);
	});
});
