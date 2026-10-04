<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { daysSince, formatPrice, formatPricePerM2, sourceInitial } from '$lib/format';
	import SourceChip from './SourceChip.svelte';
	import type { ListingModel } from '$lib/api/client';

	let {
		listing,
		viewed = false,
		onclick
	}: { listing: ListingModel; viewed?: boolean; onclick?: () => void } = $props();

	const t = getTranslatorContext();

	const pricePerM2 = $derived(
		listing.price !== null && listing.size_m2 !== null
			? formatPricePerM2(listing.price, listing.size_m2)
			: null
	);

	const freshness = $derived.by(() => {
		const days = daysSince(listing.first_seen_at);
		return days < 1 ? t.t('new') : t.tn('{count} day watched', '{count} days watched', days);
	});
</script>

<a
	class="card"
	class:card--viewed={viewed}
	href={listing.url}
	target="_blank"
	rel="noopener noreferrer"
	{onclick}
>
	<!-- the API carries no photo field, the letter fallback is the photo slot -->
	<div class="card__photo">
		<span class="card__photo-fallback">{sourceInitial(listing.source)}</span>
	</div>

	<div class="card__body">
		<div class="card__price-line">
			{#if listing.price !== null}
				<span class="card__price">{formatPrice(listing.price)}</span>
			{/if}
			{#if listing.price_drop_from !== null}
				<span class="card__badge card__badge--drop">
					{t.t('price drop from {old_price}', { old_price: formatPrice(listing.price_drop_from) })}
				</span>
			{/if}
			{#if pricePerM2}
				<span class="card__price-per-m2">{pricePerM2}</span>
			{/if}
		</div>

		<div class="card__detail-line">
			{#if listing.disposition_raw_text}<span>{listing.disposition_raw_text}</span>{/if}
			{#if listing.size_m2 !== null}<span>{listing.size_m2}&nbsp;m²</span>{/if}
		</div>

		{#if listing.location_raw_text}
			<div class="card__location">{listing.location_raw_text}</div>
		{/if}

		<div class="card__chips">
			<span class="card__badge card__badge--freshness">{freshness}</span>
			<SourceChip source={listing.source} />
			{#each listing.sibling_sources as sibling (sibling.source)}
				<SourceChip source={sibling.source} />
			{/each}
		</div>
	</div>
</a>

<style>
	.card {
		display: flex;
		gap: var(--space-3);
		padding: var(--space-3);
		border: 1px solid var(--color-line);
		border-left: 3px solid var(--color-amber);
		border-radius: var(--radius-md);
		background: var(--color-card);
		color: inherit;
		text-decoration: none;
	}

	.card--viewed {
		border-left-color: var(--color-line);
		opacity: 0.6;
	}

	.card__photo {
		flex-shrink: 0;
		width: 4rem;
		height: 4rem;
		border-radius: var(--radius-sm);
		background: var(--color-ground);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.card__photo-fallback {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--color-bronze);
	}

	.card__body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.card__price-line {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.card__price {
		font-size: 1.0625rem;
		font-weight: 700;
	}

	.card__price-per-m2 {
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	.card__detail-line {
		display: flex;
		gap: var(--space-2);
		font-size: 0.875rem;
	}

	.card__location {
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	.card__chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1);
		margin-top: var(--space-1);
	}

	.card__badge {
		display: inline-flex;
		align-items: center;
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-full);
		font-size: 0.6875rem;
		font-weight: 600;
	}

	.card__badge--drop {
		background: var(--color-olive);
		color: var(--color-ground);
	}

	.card__badge--freshness {
		border: 1px solid var(--color-amber);
		color: var(--color-bronze);
	}
</style>
