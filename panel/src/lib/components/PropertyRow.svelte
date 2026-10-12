<script lang="ts">
	import type { TrackedPropertyModel } from '$lib/api/client';
	import { sourceInitial } from '$lib/format';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { factsOf } from '$lib/property-detail';
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
		listing: TrackedPropertyModel;
		id: string;
		score: number | null;
		selected: boolean;
		onselect: () => void;
	} = $props();

	const t = getTranslatorContext();

	const portal = $derived(shownPortal(listing.source));
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
	<span class="property-row__thumb">
		{#if portal}
			<img class="property-row__logo" src={portal.logo} alt="" />
		{:else}
			{sourceInitial(listing.source)}
		{/if}
	</span>
	<span class="property-row__text">
		<span class="property-row__price">{listing.price === null ? '–' : t.price(listing.price)}</span>
		<span class="property-row__facts">{facts}</span>
	</span>
	{#if favourite}
		<span class="property-row__star" aria-label={t.t('Favourite')}>★</span>
	{/if}
	{#if score !== null}
		<span class="property-row__score">{score}</span>
	{/if}
</div>

<style>
	.property-row {
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

	.property-row__thumb {
		display: grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: var(--radius-sm);
		background: var(--color-ground);
		color: var(--color-bronze);
		font-weight: 700;
	}

	.property-row__logo {
		width: 1.75rem;
		height: 1.75rem;
		object-fit: contain;
	}

	.property-row__text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.property-row__price {
		font-weight: 700;
	}

	.property-row__facts {
		overflow: hidden;
		color: var(--color-bronze);
		font-size: 0.8125rem;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.property-row__star {
		color: var(--color-gold);
	}

	.property-row__score {
		min-width: 2rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
</style>
