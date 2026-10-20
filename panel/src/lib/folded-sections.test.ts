import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { foldedSections, keepFoldedSections } from './folded-sections';

beforeEach(() => {
	localStorage.clear();
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe('foldedSections', () => {
	test('reads back the sections kept folded', () => {
		keepFoldedSections(['viewed', 'new']);
		expect(foldedSections()).toEqual(['new', 'viewed']);
	});

	test('folds nothing when nothing was kept', () => {
		expect(foldedSections()).toEqual([]);
	});

	test('ignores what it does not know as a section', () => {
		localStorage.setItem('rentczecher.foldedSections', '["new", "archive", 3]');
		expect(foldedSections()).toEqual(['new']);
	});

	test('folds nothing when the storage is refused', () => {
		vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
			throw new Error('refused');
		});
		expect(foldedSections()).toEqual([]);
	});
});
