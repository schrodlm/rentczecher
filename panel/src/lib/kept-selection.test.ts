import { afterEach, describe, expect, test, vi } from 'vitest';
import { keepSelection, takeKeptSelection } from './kept-selection';

afterEach(() => {
	sessionStorage.clear();
	vi.restoreAllMocks();
});

describe('kept selection', () => {
	test('gives back the kept selection once', () => {
		keepSelection({ profileId: 'p1', propertyId: 'x' });
		expect(takeKeptSelection()).toEqual({ profileId: 'p1', propertyId: 'x' });
		expect(takeKeptSelection()).toBeNull();
	});

	test('keeps a profile with no listing selected', () => {
		keepSelection({ profileId: 'p1', propertyId: null });
		expect(takeKeptSelection()).toEqual({ profileId: 'p1', propertyId: null });
	});

	test('gives back nothing when nothing was kept', () => {
		expect(takeKeptSelection()).toBeNull();
	});

	test('gives back nothing for a stored value it did not write', () => {
		sessionStorage.setItem('rentczecher.keptSelection', 'not json');
		expect(takeKeptSelection()).toBeNull();
		sessionStorage.setItem('rentczecher.keptSelection', '{"propertyId": "x"}');
		expect(takeKeptSelection()).toBeNull();
	});

	test('keeps and gives back nothing when the browser refuses its storage', () => {
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new DOMException('refused', 'SecurityError');
		});
		vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
			throw new DOMException('refused', 'SecurityError');
		});
		expect(() => keepSelection({ profileId: 'p1', propertyId: 'x' })).not.toThrow();
		expect(takeKeptSelection()).toBeNull();
	});
});
