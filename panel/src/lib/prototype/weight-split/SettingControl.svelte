<!-- PROTOTYPE, throwaway. The setting a preference scores against. -->
<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import LayoutChips from '$lib/forms/LayoutChips.svelte';
	import PreferredPlaces from '$lib/forms/PreferredPlaces.svelte';
	import ValueSlider from '$lib/forms/ValueSlider.svelte';
	import { LAND_SCALE, RENT_SCALE, SIZE_SCALE } from '$lib/forms/scale';
	import type { SplitState, Wish } from './split.svelte';

	let { split, wish }: { split: SplitState; wish: Wish } = $props();

	const PLACES: NamedPlace[] = [
		{ kind: 'mestska_cast', code: 500186, name: 'Praha 7', obec: 'Praha', okres: null },
		{ kind: 'mestska_cast', code: 500208, name: 'Praha 8', obec: 'Praha', okres: null },
		{ kind: 'cast_obce', code: 490067, name: 'Holešovice', obec: 'Praha', okres: null },
		{ kind: 'cast_obce', code: 400064, name: 'Karlín', obec: 'Praha', okres: null }
	];

	async function search(query: string): Promise<NamedPlace[]> {
		return PLACES.filter((place) => (place.name ?? '').toLowerCase().startsWith(query.toLowerCase()));
	}

</script>

{#if wish === 'price'}
	<ValueSlider scale={RENT_SCALE} bind:value={split.settings.max_good_price} name="Dobrá cena" unit="Kč" placeholder="dobrá cena" />
{:else if wish === 'size'}
	<ValueSlider scale={SIZE_SCALE} bind:value={split.settings.ideal_size_m2} name="Ideální velikost" unit="m²" placeholder="ideální velikost" />
{:else if wish === 'land'}
	<ValueSlider scale={LAND_SCALE} bind:value={split.settings.ideal_land_m2} name="Ideální pozemek" unit="m²" placeholder="ideální pozemek" />
{:else if wish === 'layout'}
	<LayoutChips bind:selected={split.settings.preferred_dispositions} name="Oblíbené dispozice" />
{:else}
	<PreferredPlaces bind:places={split.settings.preferred_places} {search} placeholder="Přidat část oblasti hledání" />
{/if}
