import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import ListingCard from './ListingCard.svelte';
import { listing } from '$lib/test-support/listing';

describe('ListingCard', () => {
	test('opens the listing url in a new tab on click', async () => {
		const { getByRole } = await renderWithTranslator(ListingCard, {
			score: null,
			onfavourite: () => {},
			listing: listing('sreality:1', { url: 'https://sreality.cz/detail/42' })
		});
		const link = getByRole('link');
		expect(link).toHaveAttribute('href', 'https://sreality.cz/detail/42');
		expect(link).toHaveAttribute('target', '_blank');
		expect(link).toHaveAttribute('rel', 'noopener noreferrer');
	});

	test('shows price and price per m²', async () => {
		const { getByText } = await renderWithTranslator(ListingCard, {
			score: null,
			onfavourite: () => {},
			listing: listing('sreality:1', { price: 21000, size_m2: 52 })
		});
		expect(getByText('21 000 Kč')).toBeInTheDocument();
		expect(getByText('404 Kč/m²')).toBeInTheDocument();
	});

	test('shows a price-drop badge naming the previous price when dropped', async () => {
		const { getByText } = await renderWithTranslator(ListingCard, {
			score: null,
			onfavourite: () => {},
			listing: listing('sreality:1', { price: 19000, price_drop_from: 21000 })
		});
		expect(getByText('sleva z 21 000 Kč')).toBeInTheDocument();
	});

	test('omits the price-drop badge when there is no drop', async () => {
		const { queryByText } = await renderWithTranslator(ListingCard, {
			score: null,
			onfavourite: () => {},
			listing: listing('sreality:1', { price_drop_from: null })
		});
		expect(queryByText(/sleva/)).not.toBeInTheDocument();
	});

	test('renders a source chip per sibling on other portals', async () => {
		const { getByText } = await renderWithTranslator(ListingCard, {
			score: null,
			onfavourite: () => {},
			listing: listing('sreality:1', {
				sibling_sources: [{ source: 'bezrealitky', url: 'https://bezrealitky.cz/detail/2' }]
			})
		});
		expect(getByText('Sreality')).toBeInTheDocument();
		expect(getByText('Bezrealitky')).toBeInTheDocument();
	});

	test('shows the portal\'s logo where a photo would be', async () => {
		const { container } = await renderWithTranslator(ListingCard, { score: null, onfavourite: () => {}, listing: listing('sreality:1') });
		expect(container.querySelector('.card__photo img')).not.toBeNull();
		expect(container.querySelector('.card__photo-fallback')).toBeNull();
	});

	describe('disposition', () => {
		test('shows the disposition code rather than the raw text', async () => {
			const { getByText, queryByText } = await renderWithTranslator(ListingCard, {
				score: null,
				onfavourite: () => {},
				listing: listing('sreality:1', { disposition_raw_text: 'Garsoniéra', disposition: '1+kk' })
			});
			expect(getByText('1+kk')).toBeInTheDocument();
			expect(queryByText('Garsoniéra')).not.toBeInTheDocument();
		});

		test('names an atypical layout in words', async () => {
			const { getByText } = await renderWithTranslator(ListingCard, {
				score: null,
				onfavourite: () => {},
				listing: listing('sreality:1', { disposition_raw_text: 'Atypický', disposition: 'atypicky' })
			});
			expect(getByText('atypická dispozice')).toBeInTheDocument();
		});

		test('falls back to the raw text when it names no layout', async () => {
			const { getByText } = await renderWithTranslator(ListingCard, {
				score: null,
				onfavourite: () => {},
				listing: listing('sreality:1', { disposition_raw_text: 'Rodinný', disposition: null })
			});
			expect(getByText('Rodinný')).toBeInTheDocument();
		});

		test('shows no disposition when none was scraped', async () => {
			const { container } = await renderWithTranslator(ListingCard, {
				score: null,
				onfavourite: () => {},
				listing: listing('sreality:1', { disposition_raw_text: null, disposition: null, size_m2: null })
			});
			expect(container.querySelector('.card__detail-line')?.children).toHaveLength(0);
		});
	});

	test('shows its score as a ring', async () => {
		const { getByRole } = await renderWithTranslator(ListingCard, { score: 64, onfavourite: () => {}, listing: listing('sreality:1') });
		expect(getByRole('img', { name: 'Skóre 64 ze 100' })).toBeInTheDocument();
	});

	test('shows no ring while unscored', async () => {
		const { queryByRole } = await renderWithTranslator(ListingCard, { score: null, onfavourite: () => {}, listing: listing('sreality:1') });
		expect(queryByRole('img', { name: /Skóre/ })).toBeNull();
	});

	describe('favourite', () => {
		test('marks a listing a favourite with its star, without opening it', async () => {
			const onfavourite = vi.fn();
			const onclick = vi.fn();
			const { getByRole } = await renderWithTranslator(ListingCard, {
				score: null,
				onfavourite,
				onclick,
				listing: listing('sreality:1')
			});
			await fireEvent.click(getByRole('button', { name: 'Přidat do oblíbených' }));
			expect(onfavourite).toHaveBeenCalledWith(true);
			expect(onclick).not.toHaveBeenCalled();
		});

		test('takes a favourite out with its star', async () => {
			const onfavourite = vi.fn();
			const { getByRole } = await renderWithTranslator(ListingCard, {
				score: null,
				onfavourite,
				listing: listing('sreality:1', { favourited_at: '2026-10-09T08:00:00Z' })
			});
			const star = getByRole('button', { name: 'Odebrat z oblíbených' });
			expect(star).toHaveAttribute('aria-pressed', 'true');
			await fireEvent.click(star);
			expect(onfavourite).toHaveBeenCalledWith(false);
		});

		test('marks a favourite out and never dims it, though viewed', async () => {
			const { container } = await renderWithTranslator(ListingCard, {
				score: null,
				viewed: true,
				onfavourite: () => {},
				listing: listing('sreality:1', { favourited_at: '2026-10-09T08:00:00Z' })
			});
			expect(container.querySelector('.card--favourite')).not.toBeNull();
			expect(container.querySelector('.card--viewed')).toBeNull();
		});
	});
});
