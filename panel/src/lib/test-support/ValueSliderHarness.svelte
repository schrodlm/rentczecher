<script lang="ts">
	import ValueSlider from '$lib/forms/ValueSlider.svelte';
	import type { Scale } from '$lib/forms/scale';

	/* Binds a ValueSlider the way a form does and shows its value, so a test
	reads what the slider wrote back. */
	let { scale, value }: { scale: Scale; value: number | null } = $props();

	// svelte-ignore state_referenced_locally
	let bound = $state(value);
</script>

<ValueSlider {scale} bind:value={bound} name="Ideální velikost" unit="m²" placeholder="ideální velikost" />
<output data-testid="value">{JSON.stringify(bound)}</output>
