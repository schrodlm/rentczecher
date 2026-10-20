<script lang="ts">
	import { untrack } from 'svelte';
	import type { GalleryModel, TrackedPropertyModel, PostingPricesModel } from '$lib/api/client';
	import { foldedSections, keepFoldedSections, SECTIONS, type Section } from '$lib/folded-sections';
	import type { NearbyStore } from '$lib/nearby/nearby-store.svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { activeFacets, noFilter, passes, type PropertyFilter } from '$lib/property-filter';
	import { naturalOrder, SORT_FIELDS, sortProperties, type PropertyOrder } from '$lib/property-order';
	import { scoreProperty, type ScoringPreferences } from '$lib/scoring/score';
	import FilterChips from './FilterChips.svelte';
	import FilterMenu from './FilterMenu.svelte';
	import PropertyDetail from './PropertyDetail.svelte';
	import PropertyRow from './PropertyRow.svelte';
	import SortMenu from './SortMenu.svelte';

	/* Where a listing sits in the list: its section, and the date the section
	orders it by. */
	type Placement = { section: Section; date: string };

	// A row has room for the distances of three kinds.
	const ROW_NEARBY_KINDS = 3;

	/* A profile's listings as a list beside the selected one's details. The
	keys work wherever the focus is outside a text field or a dialog: the
	arrows move and view, Enter opens the listing on its portal, F stars it.
	A narrow window shows one column at a time, the details over the list. */
	let {
		listings,
		preferences,
		onview,
		onfavourite,
		onmarkallviewed,
		loadPriceHistory,
		gallery,
		nearby,
		selectedId = $bindable(null)
	}: {
		listings: readonly TrackedPropertyModel[];
		preferences: ScoringPreferences | null;
		onview: (propertyId: string) => void;
		onfavourite: (propertyId: string, favourite: boolean) => void;
		onmarkallviewed: (propertyIds: string[]) => void;
		loadPriceHistory: (propertyId: string) => Promise<PostingPricesModel[]>;
		gallery: GalleryModel | null;
		nearby: NearbyStore;
		selectedId?: string | null;
	} = $props();

	const t = getTranslatorContext();
	const listId = $props.id();

	let order = $state<PropertyOrder>(naturalOrder('score'));
	let filter = $state<PropertyFilter>(noFilter());
	let priceHistory = $state<PostingPricesModel[] | null>(null);
	let detailOpen = $state(false);
	let folded = $state(foldedSections());
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
	const shown = $derived(listings.filter((listing) => passes(listing, filter, scoreOf(listing))));
	const filtering = $derived(activeFacets(filter).length > 0);
	const sections = $derived.by(() => {
		const inSection = (section: Section) =>
			sortProperties(
				shown.filter((listing) => placements.get(listing.id)?.section === section),
				shownOrder,
				scoreOf,
				(listing) => placements.get(listing.id)?.date ?? ''
			);
		return { new: inSection('new'), favourite: inSection('favourite'), viewed: inSection('viewed') };
	});
	const ordered = $derived(
		SECTIONS.flatMap((section) => (folded.includes(section) ? [] : sections[section]))
	);
	const selectedIndex = $derived(ordered.findIndex((listing) => listing.id === selectedId));
	const selected = $derived(ordered[selectedIndex] ?? null);
	const selectedRowId = $derived(selected === null ? null : rowId(selected));
	const unviewed = $derived(sections.new.some((listing) => listing.viewed_at === null));

	// A profile opens on its first listing, selected but not viewed, and a
	// selected listing that leaves the profile or the filter's view gives way
	// to the first shown again.
	$effect(() => {
		if (ordered.some((listing) => listing.id === selectedId)) return;
		selectedId = ordered[0]?.id ?? null;
	});

	// The selected listing's prices load beside it. An answer for a listing
	// no longer selected is dropped, and a failed one leaves the panel out.
	$effect(() => {
		const propertyId = selected?.id;
		priceHistory = null;
		if (propertyId === undefined) return;
		loadPriceHistory(propertyId)
			.then((postings) => {
				if (selected?.id === propertyId) priceHistory = postings;
			})
			.catch(() => {});
	});

	// The arrows can move the selection off the visible rows, so it is
	// brought back into view.
	$effect(() => {
		if (selectedRowId !== null) document.getElementById(selectedRowId)?.scrollIntoView({ block: 'nearest' });
	});

	function placementOf(listing: TrackedPropertyModel): Placement {
		if (listing.favourited_at !== null) return { section: 'favourite', date: listing.favourited_at };
		if (listing.viewed_at !== null) return { section: 'viewed', date: listing.viewed_at };
		return { section: 'new', date: listing.first_seen_at };
	}

	function scoreOf(listing: TrackedPropertyModel): number | null {
		return preferences === null ? null : scoreProperty(listing, preferences);
	}

	function toggleSection(section: Section): void {
		folded = folded.includes(section) ? folded.filter((each) => each !== section) : [...folded, section];
		keepFoldedSections(folded);
	}

	function rowId(listing: TrackedPropertyModel): string {
		return `${listId}-${listing.id}`;
	}

	// A narrow window shows the details over the list, so only a click opens
	// them there: moving with the arrows keeps the list, and its focus, in view.
	function select(listing: TrackedPropertyModel, openDetail: boolean): void {
		selectedId = listing.id;
		if (openDetail) detailOpen = true;
		if (listing.viewed_at === null) onview(listing.id);
	}

	function step(by: 1 | -1): void {
		const next = ordered[selectedIndex + by];
		if (next !== undefined) select(next, false);
	}

	// Only what the filter shows, since only that was there to be seen.
	function markShownViewed(): void {
		onmarkallviewed(sections.new.filter((listing) => listing.viewed_at === null).map((listing) => listing.id));
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

{#snippet section(key: Section, title: string, sectionListings: TrackedPropertyModel[])}
	{@const open = !folded.includes(key)}
	<div class="inbox__section" role="group" aria-label={title}>
		<h2 class="inbox__heading">
			<button type="button" class="inbox__fold" aria-expanded={open} onclick={() => toggleSection(key)}>
				<span class="inbox__fold-arrow" class:inbox__fold-arrow--open={open} aria-hidden="true">▸</span>
				{title}
				<span class="inbox__fold-count">{sectionListings.length}</span>
			</button>
		</h2>
		{#if open}
			{#each sectionListings as listing (listing.id)}
				<PropertyRow
					{listing}
					id={rowId(listing)}
					score={scoreOf(listing)}
					nearby={listing.point === null ? [] : nearby.distancesFrom(listing.point, ROW_NEARBY_KINDS)}
					selected={selected?.id === listing.id}
					onselect={() => select(listing, true)}
				/>
			{/each}
		{/if}
	</div>
{/snippet}

<div class="inbox" class:inbox--detail-open={detailOpen}>
	<div class="inbox__list">
		<div class="inbox__tools">
			{#if unviewed}
				<button type="button" class="inbox__mark-all" onclick={markShownViewed}>{t.t('Mark all viewed')}</button>
			{/if}
			<FilterMenu bind:filter {listings} scored={preferences !== null} />
			<SortMenu bind:order={() => shownOrder, (chosen) => (order = chosen)} {fields} />
		</div>
		<FilterChips bind:filter shown={shown.length} count={listings.length} />
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div
			bind:this={rows}
			class="inbox__rows"
			role="listbox"
			tabindex="0"
			aria-label={t.t('Listings')}
			aria-activedescendant={selectedRowId ?? undefined}
		>
			{#if filtering && shown.length === 0}
				<div class="inbox__unmatched">
					<p class="inbox__empty">{t.t('Nothing matches the filter')}</p>
					<button type="button" class="inbox__mark-all" onclick={() => (filter = noFilter())}>
						{t.t('Clear the filter')}
					</button>
				</div>
			{:else}
				{@render section('new', t.t('New'), sections.new)}
				{#if sections.new.length === 0 && !folded.includes('new')}
					<p class="inbox__empty">{t.t('No new listings')}</p>
				{/if}
				{#if sections.favourite.length > 0}
					{@render section('favourite', t.t('Favourites'), sections.favourite)}
				{/if}
				{#if sections.viewed.length > 0}
					{@render section('viewed', t.t('Viewed'), sections.viewed)}
				{/if}
			{/if}
		</div>
	</div>

	<div class="inbox__pane">
		<div class="inbox__detail" bind:this={detail}>
			<button type="button" class="inbox__back" onclick={backToList}>← {t.t('Back to the list')}</button>
			{#if selected}
				<PropertyDetail
					listing={selected}
					{listings}
					{preferences}
					{priceHistory}
					{gallery}
					{nearby}
					onfavourite={(favourite) => onfavourite(selected.id, favourite)}
				/>
			{:else if listings.length === 0}
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
		grid-template-columns: minmax(24rem, 34rem) 1fr;
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
		margin: var(--space-4) 0 var(--space-1);
		font-size: 0.75rem;
	}

	.inbox__fold {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-1) var(--space-2);
		border: none;
		border-radius: var(--radius-sm);
		background: none;
		color: var(--color-bronze);
		font: inherit;
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		cursor: pointer;
	}

	.inbox__fold:hover {
		background: var(--color-card);
		color: var(--color-ink);
	}

	.inbox__fold-arrow {
		transition: transform 0.15s ease;
	}

	.inbox__fold-arrow--open {
		transform: rotate(90deg);
	}

	.inbox__fold-count {
		margin-left: auto;
		font-weight: 600;
		letter-spacing: 0;
	}

	@media (prefers-reduced-motion: reduce) {
		.inbox__fold-arrow {
			transition: none;
		}
	}

	.inbox__unmatched {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-1);
		margin: var(--space-4) var(--space-2);
	}

	.inbox__unmatched .inbox__empty {
		margin: 0;
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
