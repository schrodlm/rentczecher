import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import PortalHealthDot from './PortalHealthDot.svelte';

describe('PortalHealthDot', () => {
	test('labels an ok portal with its Czech status', async () => {
		const { getByLabelText } = await renderWithTranslator(PortalHealthDot, {
			portal: 'sreality',
			status: 'ok'
		});
		expect(getByLabelText('sreality: v pořádku')).toBeInTheDocument();
	});

	test('labels a broken portal distinctly from ok', async () => {
		const { getByLabelText } = await renderWithTranslator(PortalHealthDot, {
			portal: 'remax',
			status: 'broken'
		});
		expect(getByLabelText('remax: nedostupný')).toBeInTheDocument();
	});

	test('labels a zero-results portal distinctly from ok and broken', async () => {
		const { getByLabelText } = await renderWithTranslator(PortalHealthDot, {
			portal: 'bezrealitky',
			status: 'zero_results'
		});
		expect(getByLabelText('bezrealitky: bez výsledků')).toBeInTheDocument();
	});
});
