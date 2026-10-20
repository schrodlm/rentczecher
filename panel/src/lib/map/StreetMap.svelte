<script lang="ts">
	import 'leaflet/dist/leaflet.css';
	import L from 'leaflet';
	import { onMount } from 'svelte';
	import type { components } from '$lib/api/types.gen';

	type PointModel = components['schemas']['PointModel'];

	const TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
	const TILES_MAX_ZOOM = 19;
	const STREET_ZOOM = 15;

	/* A point on an OpenStreetMap street map, pinned. Over the whole window
	the wheel zooms and the arrow keys pan, while a map within the page
	leaves both to the page around it. */
	let { point, wholeWindow }: { point: PointModel; wholeWindow: boolean } = $props();

	let element = $state<HTMLElement>();
	let shown = $state.raw<{ map: L.Map; pin: L.Marker } | null>(null);

	onMount(() => {
		if (element === undefined) return;
		const map = L.map(element, { scrollWheelZoom: wholeWindow, keyboard: wholeWindow, attributionControl: false });
		L.tileLayer(TILES, { maxZoom: TILES_MAX_ZOOM }).addTo(map);
		const pin = L.marker([point.lat, point.lon], {
			icon: L.divIcon({ className: 'street-map__pin', iconSize: [18, 18] }),
			keyboard: false,
			interactive: false
		}).addTo(map);
		shown = { map, pin };
		// Leaflet measures its box once, so a map made in a hidden pane would
		// stay grey when the pane appears.
		const resizes = new ResizeObserver(() => map.invalidateSize());
		resizes.observe(element);
		return () => {
			resizes.disconnect();
			map.remove();
		};
	});

	// The details stay mounted while the selection moves from flat to flat.
	$effect(() => {
		if (shown === null) return;
		shown.map.setView([point.lat, point.lon], STREET_ZOOM);
		shown.pin.setLatLng([point.lat, point.lon]);
	});
</script>

<div class="street-map" bind:this={element}></div>

<style>
	.street-map {
		height: 100%;
		border-radius: var(--radius-md);
		background: var(--color-card);
		font: inherit;
	}

	/* The tiles stay light in both themes, so the pin rings in white. */
	.street-map :global(.street-map__pin) {
		border: 3px solid #fff;
		border-radius: var(--radius-full);
		background: var(--color-amber);
		box-shadow: 0 1px 4px rgb(0 0 0 / 35%);
	}

	.street-map :global(.leaflet-bar) {
		border: 1px solid var(--color-line);
		border-radius: var(--radius-sm);
		box-shadow: none;
		overflow: hidden;
	}

	.street-map :global(.leaflet-bar a) {
		border-bottom-color: var(--color-line);
		background: var(--color-card);
		color: var(--color-ink);
	}

	.street-map :global(.leaflet-bar a:hover) {
		background: var(--color-ground);
		color: var(--color-amber);
	}
</style>
