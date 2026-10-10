<script lang="ts">
	import type { ListingModel } from '$lib/api/client';
	import { formatPrice, sourceInitial } from '$lib/format';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { layoutName } from '$lib/layouts';
	import { shownPortal } from '$lib/portals';

	/* One listing in the inbox's list: enough to tell it apart and judge it at
	a glance. The list around it takes the keys, the row reports a click. */
	let {
		listing,
		id,
		score,
		selected,
		onselect
	}: {
		listing: ListingModel;
		id: string;
		score: number | null;
		selected: boolean;
		onselect: () => void;
	} = $props();

	const t = getTranslatorContext();

	const portal = $derived(shownPortal(listing.source));
	const favourite = $derived(listing.favourited_at !== null);
	const layout = $derived(
		listing.disposition === 'atypicky' ? t.t('atypical layout') : (listing.disposition ?? listing.disposition_raw_text)
	);
	const facts = $derived(
		[layout, listing.size_m2 === null ? null : `${listing.size_m2} m²`, listing.location_raw_text]
			.filter((fact) => fact !== null)
			.join(' · ')
	);
</script>

<!-- The listbox around the rows takes the keyboard, so a row only needs the click. -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
	class="listing-row"
	class:listing-row--selected={selected}
	class:listing-row--new={listing.viewed_at === null}
	class:listing-row--favourite={favourite}
	class:listing-row--viewed={listing.viewed_at !== null && !favourite}
	{id}
	role="option"
	tabindex="-1"
	aria-selected={selected}
	onclick={onselect}
>
	<span class="listing-row__thumb">
		{#if portal}
			<img class="listing-row__logo" src={portal.logo} alt="" />
		{:else}
			{sourceInitial(listing.source)}
		{/if}
	</span>
	<span class="listing-row__text">
		<span class="listing-row__price">{listing.price === null ? '–' : formatPrice(listing.price)}</span>
		<span class="listing-row__facts">{facts}</span>
	</span>
	{#if favourite}
		<span class="listing-row__star" aria-label={t.t('Favourite')}>★</span>
	{/if}
	{#if score !== null}
		<span class="listing-row__score">{score}</span>
	{/if}
</div>

<style>
	.listing-row {
		display: grid;
		grid-template-columns: 2.5rem 1fr auto auto;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-2);
		border: 1px solid transparent;
		border-left: 3px solid transparent;
		border-radius: var(--radius-md);
		cursor: pointer;
	}

	.listing-row:hover {
		background: var(--color-card);
	}

	.listing-row--new {
		border-left-color: var(--color-amber);
	}

	.listing-row--favourite {
		border-left-color: var(--color-gold);
	}

	.listing-row--selected {
		border-color: var(--color-line);
		background: var(--color-card);
	}

	.listing-row--new.listing-row--selected {
		border-left-color: var(--color-amber);
	}

	.listing-row--favourite.listing-row--selected {
		border-left-color: var(--color-gold);
	}

	.listing-row--viewed .listing-row__text,
	.listing-row--viewed .listing-row__score {
		opacity: 0.6;
	}

	.listing-row__thumb {
		display: grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: var(--radius-sm);
		background: var(--color-ground);
		color: var(--color-bronze);
		font-weight: 700;
	}

	.listing-row__logo {
		width: 1.75rem;
		height: 1.75rem;
		object-fit: contain;
	}

	.listing-row__text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.listing-row__price {
		font-weight: 700;
	}

	.listing-row__facts {
		overflow: hidden;
		color: var(--color-bronze);
		font-size: 0.8125rem;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.listing-row__star {
		color: var(--color-gold);
	}

	.listing-row__score {
		min-width: 2rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
</style>
