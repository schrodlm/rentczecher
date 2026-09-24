import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ScoreRing from './ScoreRing.svelte';

describe('ScoreRing', () => {
	test('renders nothing when score is null', async () => {
		const { container } = await renderWithTranslator(ScoreRing, { score: null });
		expect(container.querySelector('svg')).toBeNull();
		expect(container.textContent?.trim()).toBe('');
	});

	test('shows the numeric score when present', async () => {
		const { getByText } = await renderWithTranslator(ScoreRing, { score: 72 });
		expect(getByText('72')).toBeInTheDocument();
	});
});
