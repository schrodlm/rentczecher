<script lang="ts">
	import LayoutChips from '$lib/forms/LayoutChips.svelte';
	import type { Layout } from '$lib/layouts';

	/* Binds LayoutChips the way a form does and shows the picked layouts, so a
	test reads what the chips wrote back. */
	let { selected }: { selected: Layout[] } = $props();

	// svelte-ignore state_referenced_locally
	let bound = $state(selected);
</script>

<LayoutChips bind:selected={bound} name="Dispozice" />
<output data-testid="selected">{JSON.stringify(bound)}</output>
