import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ListingCard from './ListingCard.svelte';
import type { components } from '$lib/api/types.gen';

type ListingModel = components['schemas']['ListingModel'];

function listing(overrides: Partial<ListingModel> = {}): ListingModel {
	return {
		id: 'sreality:1',
		source: 'sreality',
		url: 'https://sreality.cz/detail/1',
		title: 'Byt 2+kk',
		location: 'Praha 7 - Holešovice',
		size_m2: 52,
		disposition: '2+kk',
		first_seen_at: new Date().toISOString(),
		viewed_at: null,
		favourited_at: null,
		price: 21000,
		price_drop_from: null,
		sibling_sources: [],
		...overrides
	};
}

describe('ListingCard', () => {
	test('opens the listing url in a new tab on click', async () => {
		const { getByRole } = await renderWithTranslator(ListingCard, {
			listing: listing({ url: 'https://sreality.cz/detail/42' })
		});
		const link = getByRole('link');
		expect(link).toHaveAttribute('href', 'https://sreality.cz/detail/42');
		expect(link).toHaveAttribute('target', '_blank');
		expect(link).toHaveAttribute('rel', 'noopener noreferrer');
	});

	test('shows price, price per m², disposition, and size', async () => {
		const { getByText } = await renderWithTranslator(ListingCard, {
			listing: listing({ price: 21000, size_m2: 52, disposition: '2+kk' })
		});
		expect(getByText('21 000 Kč')).toBeInTheDocument();
		expect(getByText('404 Kč/m²')).toBeInTheDocument();
		expect(getByText('2+kk')).toBeInTheDocument();
	});

	test('shows a price-drop badge naming the previous price when dropped', async () => {
		const { getByText } = await renderWithTranslator(ListingCard, {
			listing: listing({ price: 19000, price_drop_from: 21000 })
		});
		expect(getByText('sleva z 21 000 Kč')).toBeInTheDocument();
	});

	test('omits the price-drop badge when there is no drop', async () => {
		const { queryByText } = await renderWithTranslator(ListingCard, {
			listing: listing({ price_drop_from: null })
		});
		expect(queryByText(/sleva/)).not.toBeInTheDocument();
	});

	test('renders a source chip per sibling on other portals', async () => {
		const { getByText } = await renderWithTranslator(ListingCard, {
			listing: listing({
				source: 'sreality',
				sibling_sources: [{ source: 'bezrealitky', url: 'https://bezrealitky.cz/detail/2' }]
			})
		});
		expect(getByText('sreality')).toBeInTheDocument();
		expect(getByText('bezrealitky')).toBeInTheDocument();
	});

});
