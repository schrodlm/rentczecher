<script lang="ts">
	import type { ListingModel } from '$lib/api/client';
	import FilterMenu from '$lib/components/FilterMenu.svelte';
	import { noFilter } from '$lib/listing-filter';

	/* Binds a FilterMenu the way the inbox does and shows the filter it wrote
	back. */
	let { listings, scored }: { listings: ListingModel[]; scored: boolean } = $props();

	let filter = $state(noFilter());
</script>

<FilterMenu bind:filter {listings} {scored} />
<output data-testid="filter">{JSON.stringify(filter)}</output>
