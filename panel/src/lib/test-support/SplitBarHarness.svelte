<script lang="ts">
	import SplitBar from '$lib/scoring/SplitBar.svelte';
	import type { Weights, Wish } from '$lib/scoring/wishes';

	/* Binds a SplitBar the way the scoring section does and shows its weights,
	so a test reads what the bar wrote back. */
	let { weights, counting }: { weights: Weights; counting: Wish[] } = $props();

	// svelte-ignore state_referenced_locally
	let bound = $state(weights);

	const NAMES: Record<Wish, string> = {
		price: 'Cena',
		size: 'Velikost',
		land: 'Pozemek',
		layout: 'Dispozice',
		place: 'Místo'
	};
</script>

<SplitBar bind:weights={bound} {counting} label={(wish) => NAMES[wish]} />
<output data-testid="weights">{JSON.stringify(bound)}</output>
