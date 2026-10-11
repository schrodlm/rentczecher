<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import type { components } from '$lib/api/types.gen';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { mapPointOf, regionOf, TOWNS } from './czech-map';
	import { MapNavigation } from './navigation.svelte';

	type LocationModel = components['schemas']['LocationModel'];
	type PointModel = components['schemas']['PointModel'];

	/* Where a listing lies, shown on the map without any way to pick: its
	district drawn around it, the finest area the map holds highlighted, and
	the listing pinned at its point, or its town marked when it has none. */
	let { location, point }: { location: LocationModel; point: PointModel | null } = $props();

	const t = getTranslatorContext();
	const navigation = new MapNavigation();

	// Praha's districts are on the map, other towns sit in their okres, and a
	// listing placed only in a kraj shows the whole kraj.
	const area = $derived.by((): NamedPlace => {
		const { obvod, okres, kraj, obec } = location;
		if (obvod !== null) {
			return { kind: 'obvod', code: obvod.code, name: obvod.name, obec: obec?.name ?? null, okres: null };
		}
		if (okres !== null) return { kind: 'okres', code: okres.code, name: okres.name, obec: null, okres: null };
		return { kind: 'kraj', code: kraj.code, name: kraj.name, obec: null, okres: null };
	});
	const highlighted = $derived(regionOf(area));
	const town = $derived(location.obec === null ? null : (TOWNS.find((each) => each.code === location.obec?.code) ?? null));
	const view = $derived(navigation.view);
	const viewBox = $derived(`${view.x} ${view.y} ${view.width} ${view.height}`);
	const pin = $derived(point === null ? null : mapPointOf(point.lat, point.lon));

	$effect(() => navigation.show(area));
</script>

<svg class="place-map" {viewBox} role="img" aria-label={t.t('Map of where the listing lies')}>
	{#each navigation.districts as district (`${district.kind}:${district.code}`)}
		<path d={district.path} class="place-map__district" />
	{/each}
	{#each navigation.obvody as obvod (obvod.code)}
		<path d={obvod.path} class="place-map__district" />
	{/each}
	{#if highlighted}
		<path d={highlighted.path} class="place-map__area" />
	{/if}
	{#if pin}
		<circle cx={pin[0]} cy={pin[1]} r={view.width / 110} class="place-map__pin" />
	{:else if town && location.obvod === null}
		<circle cx={town.x} cy={town.y} r={view.width / 90} class="place-map__town" />
	{/if}
</svg>

<style>
	.place-map {
		width: 100%;
		height: 100%;
	}

	.place-map__district {
		fill: var(--color-ground);
		stroke: var(--color-line);
		stroke-width: 1.5;
		vector-effect: non-scaling-stroke;
	}

	.place-map__area {
		fill: color-mix(in srgb, var(--color-amber) 45%, var(--color-card));
		stroke: var(--color-bronze);
		stroke-width: 2;
		vector-effect: non-scaling-stroke;
	}

	.place-map__pin {
		fill: var(--color-bronze);
	}

	.place-map__town {
		fill: var(--color-bronze);
		stroke: var(--color-card);
		stroke-width: 2;
		vector-effect: non-scaling-stroke;
	}
</style>
