<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { daysSince, formatPrice, formatPricePerM2, sourceInitial } from '$lib/format';
	import { shownPortal } from '$lib/portals';
	import ScoreRing from './ScoreRing.svelte';
	import SourceChip from './SourceChip.svelte';
	import type { ListingModel } from '$lib/api/client';

	let {
		listing,
		score,
		viewed = false,
		onclick,
		onfavourite
	}: {
		listing: ListingModel;
		score: number | null;
		viewed?: boolean;
		onclick?: () => void;
		onfavourite: (favourite: boolean) => void;
	} = $props();

	const t = getTranslatorContext();

	const pricePerM2 = $derived(
		listing.price !== null && listing.size_m2 !== null
			? formatPricePerM2(listing.price, listing.size_m2)
			: null
	);

	// A portal label naming no layout ("Rodinný") is still worth showing.
	const dispositionLabel = $derived(
		listing.disposition === 'atypicky'
			? t.t('atypical layout')
			: (listing.disposition ?? listing.disposition_raw_text)
	);

	const portal = $derived(shownPortal(listing.source));
	const favourite = $derived(listing.favourited_at !== null);

	const freshness = $derived.by(() => {
		const days = daysSince(listing.first_seen_at);
		return days < 1 ? t.t('new') : t.tn('{count} day watched', '{count} days watched', days);
	});
</script>

<!-- A button may not sit inside a link, so the star is the link's sibling. -->
<div class="card" class:card--viewed={viewed && !favourite} class:card--favourite={favourite}>
	<a class="card__link" href={listing.url} target="_blank" rel="noopener noreferrer" {onclick}>
		<!-- the API carries no photo field, so the portal stands in for one -->
		<div class="card__photo">
			{#if portal}
				<img class="card__photo-logo" src={portal.logo} alt="" />
			{:else}
				<span class="card__photo-fallback">{sourceInitial(listing.source)}</span>
			{/if}
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
				{#if dispositionLabel}<span>{dispositionLabel}</span>{/if}
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

		{#if score !== null}
			<ScoreRing {score} />
		{/if}
	</a>
	<button
		type="button"
		class="card__star"
		class:card__star--on={favourite}
		class:card__star--unscored={score === null}
		aria-pressed={favourite}
		aria-label={favourite ? t.t('Remove from favourites') : t.t('Add to favourites')}
		onclick={() => onfavourite(!favourite)}
	>
		<svg viewBox="0 0 24 24" aria-hidden="true">
			<path d="M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.3L12 17.1l-5.7 3.1 1.2-6.3-4.7-4.4 6.4-.8z" />
		</svg>
	</button>
</div>

<style>
	.card {
		position: relative;
		border: 1px solid var(--color-line);
		border-left: 3px solid var(--color-amber);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.card--viewed {
		border-left-color: var(--color-line);
		opacity: 0.6;
	}

	.card--favourite {
		border-color: var(--color-gold);
		border-left-color: var(--color-gold);
		box-shadow: 0 2px 12px color-mix(in srgb, var(--color-gold) 30%, transparent);
	}

	.card__link {
		display: flex;
		gap: var(--space-3);
		padding: var(--space-3);
		color: inherit;
		text-decoration: none;
	}

	/* Beside the score ring, level with its centre, which leaves the photo
	clear. An empty star shows only while the pointer or the keyboard is on
	its card, so it is there to use without crowding every card. */
	.card__star {
		position: absolute;
		top: calc(var(--space-3) + 1.5rem);
		right: calc(var(--space-3) + 3rem + var(--space-3));
		display: grid;
		place-items: center;
		width: 1.75rem;
		height: 1.75rem;
		padding: 0;
		border: none;
		background: none;
		cursor: pointer;
		opacity: 0;
		transform: translateY(-50%);
		transition: opacity 120ms ease-out;
	}

	.card__star--unscored {
		right: var(--space-3);
	}

	.card:hover .card__star,
	.card:focus-within .card__star,
	.card__star--on {
		opacity: 1;
	}

	.card__star svg {
		width: 1.375rem;
		height: 1.375rem;
		fill: none;
		stroke: var(--color-bronze);
		stroke-width: 1.75;
		stroke-linejoin: round;
		transition: stroke 120ms ease-out, fill 120ms ease-out;
	}

	.card__star:hover svg,
	.card__star:focus-visible svg {
		stroke: var(--color-gold);
	}

	.card__star--on svg {
		fill: var(--color-gold);
		stroke: var(--color-gold);
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

	.card__photo-logo {
		width: 2.25rem;
		height: 2.25rem;
		object-fit: contain;
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
