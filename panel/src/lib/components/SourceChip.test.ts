import { render } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import SourceChip from './SourceChip.svelte';

describe('SourceChip', () => {
	test('shows a known portal by its logo and name', () => {
		const { getByText, container } = render(SourceChip, { source: 'remax' });
		expect(getByText('RE/MAX')).toBeInTheDocument();
		expect(container.querySelector('img.chip__logo')).not.toBeNull();
	});

	test('shows an unknown source by its name and uppercased first letter', () => {
		const { getByText } = render(SourceChip, { source: 'idnes' });
		expect(getByText('idnes')).toBeInTheDocument();
		expect(getByText('I')).toBeInTheDocument();
	});
});
