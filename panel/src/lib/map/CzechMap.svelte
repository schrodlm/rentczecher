<script lang="ts">
	import { cubicInOut } from 'svelte/easing';
	import { Tween } from 'svelte/motion';
	import type { NamedPlace } from '$lib/api/client';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { KRAJE, labelName, regionOf, regionPlace, townPlace, type Region, type Town } from './czech-map';
	import { placeLabels } from './labels';
	import type { MapNavigation } from './navigation.svelte';

	let {
		navigation,
		picked,
		onpick
	}: {
		navigation: MapNavigation;
		picked: NamedPlace | null;
		onpick: (place: NamedPlace | null) => void;
	} = $props();

	const t = getTranslatorContext();

	// Text and dots keep their size on screen at every zoom, so each is a
	// share of the width in view.
	const REGION_TEXT_SHARE = 1 / 60;
	const TOWN_TEXT_SHARE = 1 / 75;
	const LABEL_GAP_SHARE = 1 / 200;

	const view = Tween.of(() => navigation.view, { duration: 800, easing: cubicInOut });
	const viewBox = $derived(`${view.current.x} ${view.current.y} ${view.current.width} ${view.current.height}`);

	function radius(town: Town, width: number): number {
		return (width / 260) * (0.55 + Math.log10(town.streets + 1) * 0.55);
	}

	// Laid out for where the zoom lands, so names hold still while it runs.
	const labels = $derived.by(() => {
		const width = navigation.view.width;
		return placeLabels(
			navigation.namedRegions.map((region) => ({
				key: `${region.kind}:${region.code}`,
				text: labelName(region),
				x: region.label[0],
				y: region.label[1]
			})),
			navigation.towns.map((town) => ({
				key: `obec:${town.code}`,
				text: town.name,
				x: town.x,
				y: town.y,
				radius: radius(town, width),
				streets: town.streets
			})),
			{ region: width * REGION_TEXT_SHARE, town: width * TOWN_TEXT_SHARE, gap: width * LABEL_GAP_SHARE }
		);
	});

	// Keys that change with the region in view, so the layers fade in anew.
	const viewKey = $derived(`${navigation.regionInView?.kind}:${navigation.regionInView?.code}`);

	const pickedRegion = $derived(picked === null ? null : regionOf(picked));
	const pickingRegionInView = $derived(pickedRegion !== null && pickedRegion === navigation.regionInView);

	function isPickedTown(town: Town): boolean {
		return picked !== null && picked.kind === 'obec' && picked.code === town.code;
	}

	function pickRegionInView(): void {
		const region = navigation.regionInView;
		if (region === null) return;
		onpick(pickingRegionInView ? null : regionPlace(region));
	}

	function pickObvod(obvod: Region): void {
		onpick(pickedRegion === obvod ? null : regionPlace(obvod));
	}

	function pickTown(town: Town): void {
		onpick(isPickedTown(town) ? null : townPlace(town));
	}
</script>

<div class="czech-map">
	<div class="czech-map__toolbar">
		<button
			type="button"
			class="czech-map__back"
			disabled={!navigation.canGoBack}
			aria-label={t.t('Back')}
			onclick={() => navigation.back()}>←</button
		>
		<nav class="czech-map__crumbs">
			<button
				type="button"
				class="czech-map__crumb"
				class:czech-map__crumb--current={navigation.kraj === null}
				aria-current={navigation.kraj === null ? 'location' : undefined}
				onclick={() => navigation.openCountry()}>{t.t('Czechia')}</button
			>
			{#if navigation.kraj}
				{@const kraj = navigation.kraj}
				<span aria-hidden="true">›</span>
				<button
					type="button"
					class="czech-map__crumb"
					class:czech-map__crumb--current={navigation.district === null || navigation.inPraha}
					aria-current={navigation.district === null || navigation.inPraha ? 'location' : undefined}
					onclick={() => navigation.openKraj(kraj)}>{kraj.name}</button
				>
			{/if}
			{#if navigation.district && !navigation.inPraha}
				<span aria-hidden="true">›</span>
				<span class="czech-map__crumb czech-map__crumb--current" aria-current="location">{navigation.district.name}</span>
			{/if}
		</nav>
		{#if navigation.regionInView}
			<button
				type="button"
				class="czech-map__whole"
				class:czech-map__whole--on={pickingRegionInView}
				onclick={pickRegionInView}
			>
				{pickingRegionInView ? t.t('Searching the whole area') : t.t('Search the whole area')}
			</button>
		{/if}
	</div>

	<!-- The map takes clicks only. Search by name is the way in by keyboard. -->
	<svg class="czech-map__map" {viewBox} role="group" aria-label={t.t('Map of Czechia')}>
		{#each KRAJE as kraj (kraj.code)}
			<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
			<path
				d={kraj.path}
				class="czech-map__kraj"
				class:czech-map__kraj--dim={navigation.kraj !== null && navigation.kraj !== kraj}
				onclick={() => navigation.openKraj(kraj)}><title>{kraj.name}</title></path
			>
		{/each}

		{#each navigation.districts as district (`${viewKey}:${district.kind}:${district.code}`)}
			<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
			<path
				d={district.path}
				class="czech-map__district czech-map__enter"
				class:czech-map__district--dim={navigation.district !== null && navigation.district !== district}
				onclick={() => navigation.openDistrict(district)}><title>{district.name}</title></path
			>
		{/each}

		{#each navigation.obvody as obvod (obvod.code)}
			<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
			<path
				d={obvod.path}
				class="czech-map__district czech-map__enter"
				class:czech-map__picked={pickedRegion === obvod}
				onclick={() => pickObvod(obvod)}><title>{obvod.name}</title></path
			>
		{/each}

		<!-- Praha's own obvody mark their pick themselves, from anywhere else it is drawn over the map. -->
		{#if pickedRegion && !(pickedRegion.kind === 'obvod' && navigation.inPraha)}
			<path d={pickedRegion.path} class="czech-map__picked czech-map__picked-outline" />
		{/if}

		{#each labels.regions as label (`${viewKey}:${label.key}`)}
			<text
				x={label.x}
				y={label.y}
				font-size={view.current.width * REGION_TEXT_SHARE}
				class="czech-map__label czech-map__label--region czech-map__enter-late">{label.text}</text
			>
		{/each}

		{#each navigation.towns as town (`${viewKey}:${town.code}`)}
			<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
			<circle
				cx={town.x}
				cy={town.y}
				r={radius(town, view.current.width)}
				class="czech-map__town czech-map__enter-late"
				class:czech-map__town--picked={isPickedTown(town)}
				onclick={() => pickTown(town)}><title>{town.name}</title></circle
			>
		{/each}

		{#each labels.towns as label (`${viewKey}:${label.key}`)}
			<text
				x={label.x}
				y={label.y}
				text-anchor={label.anchor}
				font-size={view.current.width * TOWN_TEXT_SHARE}
				class="czech-map__label czech-map__enter-late">{label.text}</text
			>
		{/each}
	</svg>

	<p class="czech-map__hint">
		{#if navigation.inPraha}
			{t.t('Click a Praha district to search there.')}
		{:else if navigation.district}
			{t.t('Click a town to search there. For a smaller village, search it by name.')}
		{:else}
			{t.t('Click a region to zoom in.')}
		{/if}
	</p>
</div>

<style>
	/* The map's shades, each mixed from the palette, so both themes follow:
	regions lean toward bronze to stand out, and toward the page to recede. */
	.czech-map {
		--map-kraj: var(--color-line);
		--map-kraj-hover: color-mix(in srgb, var(--color-line) 90%, var(--color-bronze));
		--map-kraj-dim: color-mix(in srgb, var(--color-line) 50%, var(--color-ground));
		--map-district: color-mix(in srgb, var(--color-line) 92%, var(--color-bronze));
		--map-district-hover: color-mix(in srgb, var(--color-line) 82%, var(--color-bronze));
		--map-district-dim: color-mix(in srgb, var(--color-line) 70%, var(--color-ground));

		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.czech-map__toolbar {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		min-height: 2rem;
	}

	.czech-map__back {
		width: 2rem;
		height: 2rem;
		border-radius: var(--radius-full);
		border: 1px solid var(--color-line);
		background: var(--color-card);
		color: inherit;
		cursor: pointer;
		font-size: 1rem;
	}

	.czech-map__back:disabled {
		opacity: 0.35;
		cursor: default;
	}

	.czech-map__crumbs {
		display: flex;
		flex: 1;
		gap: var(--space-1);
		align-items: center;
		font-size: 0.875rem;
		color: var(--color-bronze);
	}

	.czech-map__crumb {
		background: none;
		border: none;
		color: var(--color-bronze);
		cursor: pointer;
		padding: 0;
		text-decoration: underline;
	}

	.czech-map__crumb--current {
		color: var(--color-ink);
		font-weight: 600;
		text-decoration: none;
	}

	.czech-map__whole {
		border: 1px solid var(--color-olive);
		background: var(--color-card);
		color: var(--color-olive);
		border-radius: var(--radius-full);
		padding: var(--space-1) var(--space-3);
		cursor: pointer;
		font-weight: 600;
		font-size: 0.8125rem;
	}

	.czech-map__whole--on {
		background: var(--color-olive);
		color: var(--color-ground);
	}

	.czech-map__map {
		width: 100%;
		aspect-ratio: 900 / 522;
		background: var(--color-ground);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		user-select: none;
	}

	.czech-map__kraj,
	.czech-map__district {
		stroke: var(--color-ground);
		stroke-width: 0.8;
		vector-effect: non-scaling-stroke;
		cursor: pointer;
		transition:
			fill 200ms,
			opacity 600ms ease;
	}

	.czech-map__kraj {
		fill: var(--map-kraj);
	}

	.czech-map__kraj:hover {
		fill: var(--map-kraj-hover);
	}

	.czech-map__kraj--dim {
		fill: var(--map-kraj-dim);
	}

	.czech-map__district {
		fill: var(--map-district);
	}

	.czech-map__district:hover {
		fill: var(--map-district-hover);
	}

	.czech-map__district--dim {
		fill: var(--map-district-dim);
	}

	.czech-map__picked {
		fill: var(--color-amber);
		fill-opacity: 0.7;
	}

	.czech-map__picked-outline {
		pointer-events: none;
		stroke: var(--color-bronze);
		stroke-width: 1.5;
		vector-effect: non-scaling-stroke;
	}

	.czech-map__town {
		fill: var(--color-bronze);
		fill-opacity: 0.6;
		stroke: var(--color-ground);
		stroke-width: 0.5;
		vector-effect: non-scaling-stroke;
		cursor: pointer;
	}

	.czech-map__town:hover {
		fill-opacity: 1;
	}

	.czech-map__town--picked {
		fill: var(--color-amber);
		fill-opacity: 1;
		stroke: var(--color-ink);
		stroke-width: 1.5;
	}

	.czech-map__label {
		pointer-events: none;
		paint-order: stroke;
		stroke: var(--color-ground);
		stroke-width: 3px;
		stroke-linejoin: round;
		vector-effect: non-scaling-stroke;
		fill: var(--color-ink);
		dominant-baseline: middle;
		font-weight: 600;
	}

	.czech-map__label--region {
		text-anchor: middle;
		font-weight: 700;
		fill-opacity: 0.6;
	}

	.czech-map__hint {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	/* Layers fade in once the zoom has mostly landed. CSS animations only,
	since the app's content policy refuses the style tags script-driven
	transitions create. */
	.czech-map__enter {
		animation: czech-map-fade-in 500ms ease 250ms both;
	}

	.czech-map__enter-late {
		animation: czech-map-fade-in 450ms ease 650ms both;
	}

	@keyframes czech-map-fade-in {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}
</style>
