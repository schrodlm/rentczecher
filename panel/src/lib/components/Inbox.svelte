<script lang="ts">
	import { untrack } from 'svelte';
	import type { ListingModel } from '$lib/api/client';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { naturalOrder, SORT_FIELDS, sortListings, type ListingOrder } from '$lib/listing-order';
	import { scoreListing, type ScoringPreferences } from '$lib/scoring/score';
	import ListingDetail from './ListingDetail.svelte';
	import ListingRow from './ListingRow.svelte';
	import SortMenu from './SortMenu.svelte';

	type Section = 'new' | 'favourite' | 'viewed';

	/* Where a listing sits in the list: its section, and the date the section
	orders it by. */
	type Placement = { section: Section; date: string };

	/* A profile's listings as a list beside the selected one's details. The
	keys work wherever the focus is outside a text field or a dialog: the
	arrows move and view, Enter opens the listing on its portal, F stars it.
	A narrow window shows one column at a time, the details over the list. */
	let {
		listings,
		preferences,
		onview,
		onfavourite,
		onmarkallviewed
	}: {
		listings: readonly ListingModel[];
		preferences: ScoringPreferences | null;
		onview: (listingId: string) => void;
		onfavourite: (listingId: string, favourite: boolean) => void;
		onmarkallviewed: () => void;
	} = $props();

	const t = getTranslatorContext();
	const listId = $props.id();

	let order = $state<ListingOrder>(naturalOrder('score'));
	let selectedId = $state<string | null>(null);
	let detailOpen = $state(false);
	let detail = $state<HTMLElement>();
	let rows = $state<HTMLElement>();

	// Unscored listings cannot go by score, so they go newest first until a
	// preference counts again, when the chosen order comes back.
	const fields = $derived(preferences === null ? SORT_FIELDS.filter((field) => field !== 'score') : SORT_FIELDS);
	const shownOrder = $derived(fields.includes(order.field) ? order : naturalOrder('date'));
	// Each listing keeps the place it loaded in until the listings load again,
	// so viewing or starring never moves a row from under you.
	const placements = $derived.by(() => {
		const loaded = listings;
		return untrack(() => new Map(loaded.map((listing) => [listing.id, placementOf(listing)])));
	});
	const sections = $derived.by(() => {
		const inSection = (section: Section) =>
			sortListings(
				listings.filter((listing) => placements.get(listing.id)?.section === section),
				shownOrder,
				scoreOf,
				(listing) => placements.get(listing.id)?.date ?? ''
			);
		return { new: inSection('new'), favourite: inSection('favourite'), viewed: inSection('viewed') };
	});
	const ordered = $derived([...sections.new, ...sections.favourite, ...sections.viewed]);
	const selectedIndex = $derived(ordered.findIndex((listing) => listing.id === selectedId));
	const selected = $derived(ordered[selectedIndex] ?? null);
	const selectedRowId = $derived(selected === null ? null : rowId(selected));
	const unviewed = $derived(sections.new.some((listing) => listing.viewed_at === null));

	// A profile opens on its first listing, selected but not viewed, and a
	// selected listing that leaves the profile gives way to the first again.
	$effect(() => {
		if (listings.some((listing) => listing.id === selectedId)) return;
		selectedId = ordered[0]?.id ?? null;
	});

	// The arrows can move the selection off the visible rows, so it is
	// brought back into view.
	$effect(() => {
		if (selectedRowId !== null) document.getElementById(selectedRowId)?.scrollIntoView({ block: 'nearest' });
	});

	function placementOf(listing: ListingModel): Placement {
		if (listing.favourited_at !== null) return { section: 'favourite', date: listing.favourited_at };
		if (listing.viewed_at !== null) return { section: 'viewed', date: listing.viewed_at };
		return { section: 'new', date: listing.first_seen_at };
	}

	function scoreOf(listing: ListingModel): number | null {
		return preferences === null ? null : scoreListing(listing, preferences);
	}

	function rowId(listing: ListingModel): string {
		return `${listId}-${listing.id}`;
	}

	// A narrow window shows the details over the list, so only a click opens
	// them there: moving with the arrows keeps the list, and its focus, in view.
	function select(listing: ListingModel, openDetail: boolean): void {
		selectedId = listing.id;
		if (openDetail) detailOpen = true;
		if (listing.viewed_at === null) onview(listing.id);
	}

	function step(by: 1 | -1): void {
		const next = ordered[selectedIndex + by];
		if (next !== undefined) select(next, false);
	}

	function backToList(): void {
		detailOpen = false;
		rows?.focus();
	}

	function onkeydown(event: KeyboardEvent): void {
		if (selected === null || event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
		// Typing and an open modal dialog keep their keys, even once its focus has
		// fallen to the page, and Enter on a button or link stays that control's own.
		if (document.querySelector('[aria-modal="true"]') !== null) return;
		const target = event.target instanceof Element ? event.target : null;
		if (target?.closest('input, textarea, select, [contenteditable]')) return;
		if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			step(event.key === 'ArrowDown' ? 1 : -1);
		} else if (event.key === 'Enter' && !target?.closest('button, a')) {
			// Through the detail's own link, so the listing opens just as a click on
			// it does in the app's window.
			detail?.querySelector<HTMLAnchorElement>('a[href]')?.click();
		} else if (event.key === 'f' || event.key === 'F') {
			onfavourite(selected.id, selected.favourited_at === null);
		} else {
			return;
		}
		event.preventDefault();
	}
</script>

<svelte:window {onkeydown} />

{#snippet section(title: string, sectionListings: ListingModel[])}
	<div class="inbox__section" role="group" aria-label={title}>
		<h2 class="inbox__heading">{title}</h2>
		{#each sectionListings as listing (listing.id)}
			<ListingRow
				{listing}
				id={rowId(listing)}
				score={scoreOf(listing)}
				selected={selected?.id === listing.id}
				onselect={() => select(listing, true)}
			/>
		{/each}
	</div>
{/snippet}

<div class="inbox" class:inbox--detail-open={detailOpen}>
	<div class="inbox__list">
		<div class="inbox__tools">
			{#if unviewed}
				<button type="button" class="inbox__mark-all" onclick={onmarkallviewed}>{t.t('Mark all viewed')}</button>
			{/if}
			<SortMenu bind:order={() => shownOrder, (chosen) => (order = chosen)} {fields} />
		</div>
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div
			bind:this={rows}
			class="inbox__rows"
			role="listbox"
			tabindex="0"
			aria-label={t.t('Listings')}
			aria-activedescendant={selectedRowId ?? undefined}
		>
			{@render section(t.t('New'), sections.new)}
			{#if sections.new.length === 0}
				<p class="inbox__empty">{t.t('No new listings')}</p>
			{/if}
			{#if sections.favourite.length > 0}
				{@render section(t.t('Favourites'), sections.favourite)}
			{/if}
			{#if sections.viewed.length > 0}
				{@render section(t.t('Viewed'), sections.viewed)}
			{/if}
		</div>
	</div>

	<div class="inbox__pane">
		<div class="inbox__detail" bind:this={detail}>
			<button type="button" class="inbox__back" onclick={backToList}>← {t.t('Back to the list')}</button>
			{#if selected}
				<ListingDetail
					listing={selected}
					{listings}
					{preferences}
					onfavourite={(favourite) => onfavourite(selected.id, favourite)}
				/>
			{:else}
				<p class="inbox__empty">{t.t('No listings yet. A scan finds them.')}</p>
			{/if}
		</div>
		{#if selectedIndex > 0}
			<button
				type="button"
				class="inbox__step inbox__step--previous"
				aria-label={t.t('Previous listing')}
				onclick={() => step(-1)}
			>
				‹
			</button>
		{/if}
		{#if selectedIndex < ordered.length - 1}
			<button
				type="button"
				class="inbox__step inbox__step--next"
				aria-label={t.t('Next listing')}
				onclick={() => step(1)}
			>
				›
			</button>
		{/if}
	</div>
</div>

<style>
	.inbox {
		display: grid;
		grid-template-columns: minmax(20rem, 26rem) 1fr;
		flex: 1;
		min-height: 0;
	}

	.inbox__list {
		display: flex;
		flex-direction: column;
		min-height: 0;
		border-right: 1px solid var(--color-line);
	}

	.inbox__tools {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-3) 0;
	}

	.inbox__mark-all {
		padding: 0;
		border: none;
		background: none;
		color: var(--color-bronze);
		font-size: 0.8125rem;
		cursor: pointer;
	}

	.inbox__mark-all:hover {
		text-decoration: underline;
	}

	.inbox__rows {
		flex: 1;
		overflow-y: auto;
		padding: 0 var(--space-3) var(--space-3);
	}

	.inbox__rows:focus-visible {
		outline: 2px solid color-mix(in srgb, var(--color-amber) 60%, transparent);
		outline-offset: -2px;
	}

	.inbox__section {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.inbox__heading {
		margin: var(--space-4) var(--space-2) var(--space-1);
		color: var(--color-bronze);
		font-size: 0.75rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}

	.inbox__empty {
		margin: var(--space-2);
		color: var(--color-bronze);
		font-size: 0.875rem;
	}

	/* Holds the steps still at the middle of the column while the details
	scroll under them. */
	.inbox__pane {
		position: relative;
		display: flex;
		min-height: 0;
	}

	.inbox__detail {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-6) 4.75rem;
	}

	.inbox__back {
		display: none;
		margin-bottom: var(--space-4);
		padding: var(--space-1) var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		color: var(--color-ink);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.inbox__step {
		position: absolute;
		top: 50%;
		display: grid;
		place-items: center;
		width: 3rem;
		height: 3rem;
		padding: 0 0 0.25rem;
		border: 1px solid var(--color-line);
		border-radius: 50%;
		background: var(--color-card);
		box-shadow: 0 2px 8px color-mix(in srgb, var(--color-ink) 14%, transparent);
		color: var(--color-ink);
		font-size: 2rem;
		line-height: 1;
		cursor: pointer;
		transform: translateY(-50%);
	}

	.inbox__step:hover {
		border-color: var(--color-amber);
		color: var(--color-amber);
	}

	.inbox__step--previous {
		left: var(--space-4);
	}

	.inbox__step--next {
		right: var(--space-6);
	}

	/* Too narrow for both columns, so one shows at a time and selecting a row
	brings its details over the list. */
	@media (max-width: 60rem) {
		.inbox {
			grid-template-columns: 1fr;
		}

		.inbox__pane,
		.inbox--detail-open .inbox__list {
			display: none;
		}

		.inbox--detail-open .inbox__pane {
			display: flex;
		}

		.inbox__back {
			display: inline-flex;
		}

		.inbox__detail {
			padding: var(--space-4) 3.5rem;
		}

		.inbox__step {
			width: 2.5rem;
			height: 2.5rem;
			font-size: 1.625rem;
		}

		.inbox__step--previous {
			left: var(--space-2);
		}

		.inbox__step--next {
			right: var(--space-4);
		}
	}
</style>
