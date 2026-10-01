import { render } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import SourceChip from './SourceChip.svelte';

describe('SourceChip', () => {
	test('shows the source name and its uppercased first letter', () => {
		const { getByText } = render(SourceChip, { source: 'bezrealitky' });
		expect(getByText('bezrealitky')).toBeInTheDocument();
		expect(getByText('B')).toBeInTheDocument();
	});
});
