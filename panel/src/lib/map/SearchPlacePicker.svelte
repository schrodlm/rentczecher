<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import PlaceSearch from '$lib/components/PlaceSearch.svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { placeLabel } from '$lib/places';
	import CzechMap from './CzechMap.svelte';
	import { MapNavigation } from './navigation.svelte';

	let {
		search,
		place,
		onchange
	}: {
		search: (query: string) => Promise<NamedPlace[]>;
		place: NamedPlace | null;
		onchange: (place: NamedPlace | null) => void;
	} = $props();

	const t = getTranslatorContext();
	const navigation = new MapNavigation();

	function pickByName(found: NamedPlace): void {
		onchange(found);
		navigation.show(found);
	}
</script>

<div class="search-place-picker">
	<div class="search-place-picker__top">
		<PlaceSearch
			{search}
			placeholder={t.t('Search a place by name: a town, part of town, street...')}
			onpick={pickByName}
		/>
		<div class="search-place-picker__picked">
			{#if place}
				<span class="search-place-picker__caption">{t.t('Searching in')}</span>
				<span class="search-place-picker__chip">
					<button type="button" class="search-place-picker__chip-name" onclick={() => navigation.show(place)}
						>{placeLabel(place, t)}</button
					>
					<button
						type="button"
						class="search-place-picker__chip-clear"
						aria-label={t.t('Clear the place')}
						onclick={() => onchange(null)}>×</button
					>
				</span>
			{:else}
				<span class="search-place-picker__caption">{t.t('No place picked yet')}</span>
			{/if}
		</div>
	</div>

	<CzechMap {navigation} picked={place} onpick={onchange} />
</div>

<style>
	.search-place-picker {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.search-place-picker__top {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4);
		align-items: center;
	}

	.search-place-picker__picked {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-wrap: wrap;
	}

	.search-place-picker__caption {
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	.search-place-picker__chip {
		display: inline-flex;
		align-items: center;
		background: var(--color-card);
		border: 1px solid var(--color-amber);
		border-radius: var(--radius-full);
		padding: 0 var(--space-1) 0 var(--space-3);
		font-size: 0.875rem;
		font-weight: 600;
	}

	.search-place-picker__chip-name,
	.search-place-picker__chip-clear {
		background: none;
		border: none;
		color: inherit;
		cursor: pointer;
		padding: var(--space-1);
	}

	.search-place-picker__chip-clear {
		color: var(--color-bronze);
		font-size: 1rem;
		line-height: 1;
	}
</style>
