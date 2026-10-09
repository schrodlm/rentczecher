<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import type { components } from '$lib/api/types.gen';
	import ScoringSection from '$lib/scoring/ScoringSection.svelte';
	import type { Weights, PreferredValues } from '$lib/scoring/preferences';

	type CriteriaBody = components['schemas']['CriteriaBody'];
	type PlaceRef = components['schemas']['PlaceRefModel'];

	/* Binds a ScoringSection the way the editor does and shows the weights it
	wrote back. */
	let {
		criteria,
		searchPlace,
		preferredValues,
		weights,
		searchPlaces
	}: {
		criteria: Omit<CriteriaBody, 'place'>;
		searchPlace: NamedPlace | null;
		preferredValues: PreferredValues;
		weights: Weights;
		searchPlaces: (query: string, within: PlaceRef, kinds: PlaceRef['kind'][]) => Promise<NamedPlace[]>;
	} = $props();

	// svelte-ignore state_referenced_locally
	let boundPreferredValues = $state(preferredValues);
	// svelte-ignore state_referenced_locally
	let boundWeights = $state(weights);
</script>

<ScoringSection
	{criteria}
	{searchPlace}
	bind:preferredValues={boundPreferredValues}
	bind:weights={boundWeights}
	{searchPlaces}
/>
<output data-testid="weights">{JSON.stringify(boundWeights)}</output>
