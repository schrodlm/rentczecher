<script lang="ts">
	import SortMenu from '$lib/components/SortMenu.svelte';
	import { SORT_FIELDS, type ListingOrder } from '$lib/listing-order';

	/* Binds a SortMenu the way the feed does and shows the order it wrote back. */
	let { order }: { order: ListingOrder } = $props();

	// svelte-ignore state_referenced_locally
	let bound = $state(order);
</script>

<SortMenu bind:order={bound} fields={SORT_FIELDS} />
<output data-testid="order">{JSON.stringify(bound)}</output>
