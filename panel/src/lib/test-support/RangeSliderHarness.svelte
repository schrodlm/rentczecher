<script lang="ts">
	import RangeSlider from '$lib/forms/RangeSlider.svelte';
	import type { Scale } from '$lib/forms/scale';

	/* Binds a RangeSlider the way a form does and shows its bounds, so a test
	reads what the slider wrote back. */
	let { scale, low, high }: { scale: Scale; low: number | null; high: number | null } = $props();

	// svelte-ignore state_referenced_locally
	let boundLow = $state(low);
	// svelte-ignore state_referenced_locally
	let boundHigh = $state(high);
</script>

<RangeSlider {scale} bind:low={boundLow} bind:high={boundHigh} name="Nájem" unit="Kč" />
<output data-testid="bounds">{JSON.stringify([boundLow, boundHigh])}</output>
