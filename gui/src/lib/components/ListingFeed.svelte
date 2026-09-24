<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import ListingCard from './ListingCard.svelte';
	import type { components } from '$lib/api/types.gen';

	type ListingModel = components['schemas']['ListingModel'];

	let {
		newListings,
		viewedListings,
		onviewed,
		onmarkallviewed
	}: {
		newListings: ListingModel[];
		viewedListings: ListingModel[];
		onviewed: (listingId: string) => void;
		onmarkallviewed: () => void;
	} = $props();

	const t = getTranslatorContext();
</script>

<div class="feed">
	<section class="feed__section">
		<div class="feed__heading-row">
			<h2 class="feed__heading">{t.t('New')}</h2>
			{#if newListings.length > 0}
				<button type="button" class="feed__mark-all" onclick={onmarkallviewed}>
					{t.t('Mark all viewed')}
				</button>
			{/if}
		</div>
		{#if newListings.length === 0}
			<p class="feed__empty">{t.t('No new listings')}</p>
		{:else}
			<div class="feed__cards">
				{#each newListings as listing (listing.id)}
					<ListingCard {listing} onclick={() => onviewed(listing.id)} />
				{/each}
			</div>
		{/if}
	</section>

	{#if viewedListings.length > 0}
		<section class="feed__section feed__section--viewed">
			<h2 class="feed__heading">{t.t('Viewed')}</h2>
			<div class="feed__cards">
				{#each viewedListings as listing (listing.id)}
					<ListingCard {listing} viewed />
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
