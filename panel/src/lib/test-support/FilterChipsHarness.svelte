<script lang="ts">
	import FilterChips from '$lib/components/FilterChips.svelte';
	import type { ListingFilter } from '$lib/listing-filter';

	/* Binds FilterChips the way the inbox does and shows the filter they wrote
	back. */
	let { filter, shown, count }: { filter: ListingFilter; shown: number; count: number } = $props();

	// svelte-ignore state_referenced_locally
	let bound = $state(filter);
</script>

<FilterChips bind:filter={bound} {shown} {count} />
<output data-testid="filter">{JSON.stringify(bound)}</output>
