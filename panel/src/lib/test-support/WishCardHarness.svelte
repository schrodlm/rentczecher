<script lang="ts">
	import WishCard from '$lib/scoring/WishCard.svelte';
	import type { Importance } from '$lib/scoring/wishes';

	/* Binds a WishCard the way the scoring section does and shows its
	importance, so a test reads what the card wrote back. */
	let { importance, ready }: { importance: Importance; ready: boolean } = $props();

	// svelte-ignore state_referenced_locally
	let bound = $state(importance);
</script>

<WishCard title="Dobrá cena" bind:importance={bound} {ready} rule="Plné body do 22 000 Kč.">
	<span>nastavení</span>
</WishCard>
<output data-testid="importance">{bound}</output>
