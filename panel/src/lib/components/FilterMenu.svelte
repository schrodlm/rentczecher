<script lang="ts">
	import type { TrackedPropertyModel } from '$lib/api/client';
	import LayoutChips from '$lib/forms/LayoutChips.svelte';
	import RangeSlider from '$lib/forms/RangeSlider.svelte';
	import { Scale } from '$lib/forms/scale';
	import ValueSlider from '$lib/forms/ValueSlider.svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import {
		activeFacets,
		layoutsAmong,
		noFilter,
		portalsAmong,
		scaleAmong,
		type ListingFilter
	} from '$lib/listing-filter';
	import { shownPortal, type Portal } from '$lib/portals';

	/* A funnel button that opens the filter's controls under it, each offering
	only what the profile's listings have: their portals, their layouts, and
	ranges from their lowest to their highest. */
	let {
		filter = $bindable(),
		listings,
		scored
	}: { filter: ListingFilter; listings: readonly TrackedPropertyModel[]; scored: boolean } = $props();

	const t = getTranslatorContext();
	const panelId = $props.id();
	const SCORE_SCALE = new Scale([0, 10, 20, 30, 40, 50, 60, 70, 80, 90]);

	let open = $state(false);
	let menu = $state<HTMLElement>();

	const active = $derived(activeFacets(filter).length);
	const portals = $derived(portalsAmong(listings));
	const layouts = $derived(layoutsAmong(listings));
	// Sale prices run in millions, so their steps are coarser than rents'.
	const priceScale = $derived.by(() => {
		const highest = Math.max(0, ...listings.map((listing) => listing.price ?? 0));
		return scaleAmong(listings, (listing) => listing.price, highest > 1_000_000 ? 100_000 : 500);
	});
	const sizeScale = $derived(scaleAmong(listings, (listing) => listing.size_m2, 5));
	const landScale = $derived(scaleAmong(listings, (listing) => listing.land_m2, 50));

	function togglePortal(portal: Portal): void {
		filter.portals = filter.portals.includes(portal)
			? filter.portals.filter((picked) => picked !== portal)
			: [...filter.portals, portal];
	}

	function onwindowclick(event: MouseEvent): void {
		if (open && menu !== undefined && !menu.contains(event.target as Node)) open = false;
	}

	function onkeydown(event: KeyboardEvent): void {
		if (open && event.key === 'Escape') {
			// Only closes the panel, so a window around it stays open.
			event.preventDefault();
			open = false;
		}
	}
</script>

<svelte:window onclick={onwindowclick} {onkeydown} />

<div class="filter-menu" bind:this={menu}>
	<button
		type="button"
		class="filter-menu__button"
		class:filter-menu__button--active={active > 0}
		aria-haspopup="dialog"
		aria-expanded={open}
		aria-controls={panelId}
		onclick={() => (open = !open)}
	>
		<svg class="filter-menu__funnel" viewBox="0 0 16 16" aria-hidden="true">
			<path d="M2 3h12l-4.5 5.5V13l-3 1.5v-6z" />
		</svg>
		{t.t('Filter')}
		{#if active > 0}<span class="filter-menu__count">{active}</span>{/if}
	</button>
	{#if open}
		<div class="filter-menu__panel" id={panelId} role="dialog" aria-label={t.t('Filter')}>
			{#if portals.length > 1}
				<fieldset class="filter-menu__facet">
					<legend>{t.t('Portals')}</legend>
					<div class="filter-menu__portals">
						{#each portals as portal (portal)}
							<button
								type="button"
								class="filter-menu__portal"
								class:filter-menu__portal--on={filter.portals.includes(portal)}
								aria-pressed={filter.portals.includes(portal)}
								onclick={() => togglePortal(portal)}
							>
								<img src={shownPortal(portal)?.logo} alt="" />
								{shownPortal(portal)?.name}
							</button>
						{/each}
					</div>
				</fieldset>
			{/if}
			<label class="filter-menu__switch">
				<input type="checkbox" bind:checked={filter.onlyPriceDrops} />
				{t.t('Only price drops')}
			</label>
			{#if scored}
				<fieldset class="filter-menu__facet">
					<legend>{t.t('Score at least')}</legend>
					<ValueSlider
						scale={SCORE_SCALE}
						bind:value={filter.minimumScore}
						name={t.t('Score at least')}
						unit=""
						placeholder={t.t('any')}
					/>
				</fieldset>
			{/if}
			{#if layouts.length > 1}
				<!-- The chips are a group named already, so the facet only shows the name. -->
				<div class="filter-menu__facet">
					<span class="filter-menu__name" aria-hidden="true">{t.t('Layout')}</span>
					<LayoutChips bind:selected={filter.layouts} name={t.t('Layout')} offered={layouts} />
				</div>
			{/if}
			{#if priceScale}
				<fieldset class="filter-menu__facet">
					<legend>{t.t('Price')}</legend>
					<RangeSlider
						scale={priceScale}
						bind:low={filter.minPrice}
						bind:high={filter.maxPrice}
						name={t.t('Price')}
						unit="Kč"
					/>
				</fieldset>
			{/if}
			{#if sizeScale}
				<fieldset class="filter-menu__facet">
					<legend>{t.t('Size')}</legend>
					<RangeSlider
						scale={sizeScale}
						bind:low={filter.minSize}
						bind:high={filter.maxSize}
						name={t.t('Size')}
						unit="m²"
					/>
				</fieldset>
			{/if}
			{#if landScale}
				<fieldset class="filter-menu__facet">
					<legend>{t.t('Land')}</legend>
					<RangeSlider
						scale={landScale}
						bind:low={filter.minLand}
						bind:high={filter.maxLand}
						name={t.t('Land')}
						unit="m²"
					/>
				</fieldset>
			{/if}
			{#if active > 0}
				<button type="button" class="filter-menu__clear" onclick={() => (filter = noFilter())}>
					{t.t('Clear the filter')}
				</button>
			{/if}
		</div>
	{/if}
</div>

<style>
	.filter-menu {
		position: relative;
		display: inline-flex;
	}

	.filter-menu__button {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-2);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		color: var(--color-bronze);
		font-size: 0.8125rem;
		cursor: pointer;
	}

	.filter-menu__button:hover {
		border-color: var(--color-bronze);
	}

	.filter-menu__button--active {
		border-color: var(--color-olive);
		color: var(--color-olive);
	}

	.filter-menu__funnel {
		width: 0.875rem;
		height: 0.875rem;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.5;
		stroke-linejoin: round;
	}

	.filter-menu__button--active .filter-menu__funnel {
		fill: currentColor;
	}

	.filter-menu__count {
		min-width: 1.125rem;
		padding: 0 var(--space-1);
		border-radius: var(--radius-full);
		background: var(--color-olive);
		color: var(--color-ground);
		font-size: 0.6875rem;
		font-weight: 700;
		text-align: center;
	}

	.filter-menu__panel {
		position: absolute;
		top: calc(100% + var(--space-1));
		right: 0;
		z-index: 10;
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
		width: 22rem;
		max-width: calc(100vw - 2 * var(--space-4));
		padding: var(--space-4);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
		box-shadow: 0 6px 20px color-mix(in srgb, var(--color-olive) 20%, transparent);
	}

	.filter-menu__facet {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		border: none;
		container-type: inline-size;
	}

	.filter-menu__facet legend,
	.filter-menu__name {
		margin-bottom: var(--space-2);
		padding: 0;
		color: var(--color-bronze);
		font-size: 0.75rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}

	.filter-menu__portals {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.filter-menu__portal {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-2);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		color: inherit;
		font-size: 0.8125rem;
		cursor: pointer;
	}

	.filter-menu__portal img {
		width: 1rem;
		height: 1rem;
		object-fit: contain;
	}

	.filter-menu__portal--on {
		border-color: var(--color-olive);
		box-shadow: inset 0 0 0 1px var(--color-olive);
	}

	.filter-menu__switch {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: 0.875rem;
		cursor: pointer;
	}

	.filter-menu__switch input {
		accent-color: var(--color-olive);
	}

	.filter-menu__clear {
		align-self: flex-start;
		padding: 0;
		border: none;
		background: none;
		color: var(--color-bronze);
		font-size: 0.8125rem;
		text-decoration: underline;
		cursor: pointer;
	}
</style>
