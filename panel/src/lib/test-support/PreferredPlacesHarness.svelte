<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import PreferredPlaces from '$lib/forms/PreferredPlaces.svelte';

	/* Binds PreferredPlaces the way a form does and shows the picked places, so
	a test reads what the picker wrote back. */
	let { places, search }: { places: NamedPlace[]; search: (query: string) => Promise<NamedPlace[]> } = $props();

	// svelte-ignore state_referenced_locally
	let bound = $state(places);
</script>

<PreferredPlaces bind:places={bound} {search} placeholder="Hledat část oblasti" />
<output data-testid="places">{JSON.stringify(bound.map((place) => place.code))}</output>
