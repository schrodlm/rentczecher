<script lang="ts">
	import type { TrackedPropertyModel } from '$lib/api/client';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { factsOf, placeOf } from '$lib/property-detail';
	import PropertyPicture from './PropertyPicture.svelte';
	import ScoreRing from './ScoreRing.svelte';

	/* One listing in the inbox's list: enough to tell it apart and judge it at
	a glance. The list around it takes the keys, the row reports a click. */
	let {
		listing,
		id,
		score,
		selected,
		onselect
	}: {
		listing: TrackedPropertyModel;
		id: string;
		score: number | null;
		selected: boolean;
		onselect: () => void;
	} = $props();

	const t = getTranslatorContext();

	const favourite = $derived(listing.favourited_at !== null);
	const facts = $derived(factsOf(listing, t));
</script>

<!-- The listbox around the rows takes the focus and the keyboard, so a click on
a row focuses the list and a screen reader follows the selection from there. -->
<!-- svelte-ignore a11y_click_events_have_key_events, a11y_interactive_supports_focus -->
<div
	class="property-row"
	class:property-row--selected={selected}
	class:property-row--new={listing.viewed_at === null}
	class:property-row--favourite={favourite}
	class:property-row--viewed={listing.viewed_at !== null && !favourite}
	{id}
	role="option"
	aria-selected={selected}
	onclick={onselect}
>
	<span class="property-row__picture"><PropertyPicture {listing} /></span>
	<span class="property-row__text">
		<span class="property-row__headline">
			<span class="property-row__name"
				><span class="property-row__index">#{listing.index}</span> {placeOf(listing) ?? ''}</span
			>
			<span class="property-row__price">{listing.price === null ? '–' : t.price(listing.price)}</span>
		</span>
		<span class="property-row__facts">{facts}</span>
	</span>
	{#if favourite}
		<span class="property-row__star" aria-label={t.t('Favourite')}>★</span>
	{/if}
	{#if score !== null}
		<span class="property-row__score"><ScoreRing {score} coloured={false} /></span>
	{/if}
</div>

<style>
	.property-row {
		display: grid;
		grid-template-columns: 2.875rem 1fr auto auto;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-2) var(--space-3);
		border: 1px solid transparent;
		border-left: 3px solid transparent;
		border-radius: var(--radius-md);
		cursor: pointer;
	}

	.property-row:hover {
		background: var(--color-card);
	}

	.property-row--new {
		border-left-color: var(--color-amber);
	}

	.property-row--favourite {
		border-left-color: var(--color-gold);
	}

	.property-row--selected {
		border-color: var(--color-line);
		background: var(--color-card);
	}

	.property-row--new.property-row--selected {
		border-left-color: var(--color-amber);
	}

	.property-row--favourite.property-row--selected {
		border-left-color: var(--color-gold);
	}

	.property-row--viewed .property-row__text,
	.property-row--viewed .property-row__score {
		opacity: 0.6;
	}

	.property-row__picture {
		width: 2.875rem;
		height: 2.875rem;
	}


	.property-row__text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	/* A long place gives way before the price does. */
	.property-row__headline {
		display: flex;
		gap: 0.3em;
		min-width: 0;
		font-size: 1rem;
		font-weight: 700;
		white-space: nowrap;
	}

	.property-row__name {
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.property-row__index {
		color: var(--color-bronze);
		font-weight: 600;
	}

	.property-row__price {
		flex: none;
	}

	.property-row__price::before {
		content: '· ';
	}

	.property-row__facts {
		overflow: hidden;
		color: color-mix(in srgb, var(--color-ink) 65%, var(--color-bronze));
		font-size: 0.9375rem;
		font-weight: 500;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.property-row__star {
		color: var(--color-gold);
	}

	.property-row__score {
		width: 2.375rem;
	}
</style>
