<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import type { components } from '$lib/api/types.gen';
	import ScoringSection from '$lib/scoring/ScoringSection.svelte';
	import type { Importances, WishSettings } from '$lib/scoring/wishes';

	type CriteriaBody = components['schemas']['CriteriaBody'];
	type PlaceRef = components['schemas']['PlaceRefModel'];

	/* Binds a ScoringSection the way the editor does and shows the importances
	it wrote back. */
	let {
		criteria,
		searchPlace,
		settings,
		importances,
		searchPlaces
	}: {
		criteria: Omit<CriteriaBody, 'place'>;
		searchPlace: NamedPlace | null;
		settings: Omit<WishSettings, 'preferred_places'> & { preferred_places: NamedPlace[] };
		importances: Importances;
		searchPlaces: (query: string, within: PlaceRef, kinds: PlaceRef['kind'][]) => Promise<NamedPlace[]>;
	} = $props();

	// svelte-ignore state_referenced_locally
	let boundSettings = $state(settings);
	// svelte-ignore state_referenced_locally
	let boundImportances = $state(importances);
</script>

<ScoringSection
	{criteria}
	{searchPlace}
	bind:settings={boundSettings}
	bind:importances={boundImportances}
	{searchPlaces}
/>
<output data-testid="importances">{JSON.stringify(boundImportances)}</output>
