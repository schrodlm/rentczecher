<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { naturalOrder, SORT_FIELDS, sortListings, type ListingOrder } from '$lib/listing-order';
	import { scoreListing, type ScoringPreferences } from '$lib/scoring/score';
	import ListingCard from './ListingCard.svelte';
	import SortMenu from './SortMenu.svelte';
	import type { ListingModel } from '$lib/api/client';

	/* The new and viewed listings of a profile, each scored by its preferences,
	or unscored while no preference counts. */
	let {
		newListings,
		viewedListings,
		preferences,
		onviewed,
		onmarkallviewed
	}: {
		newListings: ListingModel[];
		viewedListings: ListingModel[];
		preferences: ScoringPreferences | null;
		onviewed: (listingId: string) => void;
		onmarkallviewed: () => void;
	} = $props();

	const t = getTranslatorContext();

	let order = $state<ListingOrder>(naturalOrder('score'));

	// Unscored listings cannot go by score, so they go newest first until a
	// preference counts again, when the chosen order comes back.
	const fields = $derived(preferences === null ? SORT_FIELDS.filter((field) => field !== 'score') : SORT_FIELDS);
	const shownOrder = $derived(fields.includes(order.field) ? order : naturalOrder('date'));
	const sortedNew = $derived(sortListings(newListings, shownOrder, scoreOf, (listing) => listing.first_seen_at));
	const sortedViewed = $derived(
		sortListings(viewedListings, shownOrder, scoreOf, (listing) => listing.viewed_at ?? listing.first_seen_at)
	);

	function scoreOf(listing: ListingModel): number | null {
		return preferences === null ? null : scoreListing(listing, preferences);
	}
</script>

<div class="feed">
	<section class="feed__section">
		<div class="feed__heading-row">
			<h2 class="feed__heading">{t.t('New')}</h2>
			<div class="feed__actions">
				{#if newListings.length > 0}
					<button type="button" class="feed__mark-all" onclick={onmarkallviewed}>
						{t.t('Mark all viewed')}
					</button>
				{/if}
				<SortMenu bind:order={() => shownOrder, (chosen) => (order = chosen)} {fields} />
			</div>
		</div>
		{#if newListings.length === 0}
			<p class="feed__empty">{t.t('No new listings')}</p>
		{:else}
			<div class="feed__cards">
				{#each sortedNew as listing (listing.id)}
					<ListingCard {listing} score={scoreOf(listing)} onclick={() => onviewed(listing.id)} />
				{/each}
			</div>
		{/if}
	</section>

	{#if viewedListings.length > 0}
		<section class="feed__section feed__section--viewed">
			<h2 class="feed__heading">{t.t('Viewed')}</h2>
			<div class="feed__cards">
				{#each sortedViewed as listing (listing.id)}
					<ListingCard {listing} score={scoreOf(listing)} viewed />
				{/each}
			</div>
		</section>
	{/if}
</div>

<style>
	.feed {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
		padding: var(--space-4) var(--space-6);
	}

	.feed__heading-row {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
	}

	.feed__actions {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.feed__heading {
		font-size: 0.875rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--color-bronze);
		margin: 0 0 var(--space-3) 0;
	}

	.feed__mark-all {
		background: none;
		border: none;
		color: var(--color-bronze);
		font-size: 0.75rem;
		cursor: pointer;
		padding: 0;
	}

	.feed__mark-all:hover {
		text-decoration: underline;
	}

	.feed__cards {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.feed__section--viewed {
		opacity: 0.7;
	}

	.feed__empty {
		color: var(--color-bronze);
	}
</style>
