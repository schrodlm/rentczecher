import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ScoreRing from './ScoreRing.svelte';

describe('ScoreRing', () => {
	test('names the score out of 100', async () => {
		const { getByRole } = await renderWithTranslator(ScoreRing, { score: 78, coloured: true });
		expect(getByRole('img', { name: 'Skóre 78 ze 100' })).toHaveTextContent('78');
	});

	test('fills the ring as far as the score goes', async () => {
		const { container } = await renderWithTranslator(ScoreRing, { score: 50, coloured: true });
		const [filled, whole] = (container.querySelector('.score-ring__fill')?.getAttribute('stroke-dasharray') ?? '')
			.split(' ')
			.map(Number);
		expect(filled / whole).toBeCloseTo(0.5);
	});

	test('colours a high score towards olive and a low one towards bronze', async () => {
		const high = await renderWithTranslator(ScoreRing, { score: 90, coloured: true });
		const low = await renderWithTranslator(ScoreRing, { score: 10, coloured: true });
		const colour = (rendered: typeof high) =>
			(rendered.container.querySelector('.score-ring') as HTMLElement).style.getPropertyValue('--score-colour');
		expect(colour(high)).toContain('var(--color-olive) 80%');
		expect(colour(low)).toContain('var(--color-amber) 20%, var(--color-bronze)');
	});

	test('keeps a plain ring to the ink whatever the score', async () => {
		const high = await renderWithTranslator(ScoreRing, { score: 90, coloured: false });
		const low = await renderWithTranslator(ScoreRing, { score: 10, coloured: false });
		const colour = (rendered: typeof high) =>
			(rendered.container.querySelector('.score-ring') as HTMLElement).style.getPropertyValue('--score-colour');
		expect([colour(high), colour(low)]).toEqual(['var(--color-ink)', 'var(--color-ink)']);
	});
});
