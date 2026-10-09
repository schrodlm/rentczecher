<script lang="ts">
	import PortalTiles from '$lib/forms/PortalTiles.svelte';
	import type { Portal } from '$lib/portals';

	/* Binds PortalTiles the way a form does and shows the picked portals, so a
	test reads what the tiles wrote back. */
	let { selected }: { selected: Portal[] } = $props();

	// svelte-ignore state_referenced_locally
	let bound = $state(selected);
</script>

<PortalTiles bind:selected={bound} name="Portály" />
<output data-testid="selected">{JSON.stringify(bound)}</output>
