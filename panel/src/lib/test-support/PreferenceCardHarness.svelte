<script lang="ts">
	import PreferenceCard from '$lib/scoring/PreferenceCard.svelte';

	/* Renders a PreferenceCard with a stand-in setting inside it. */
	let { on, ready, ontoggle }: { on: boolean; ready: boolean; ontoggle: () => void } = $props();
</script>

<PreferenceCard preference="price" title="Preferovaná cena" {on} weight={45} {ready} rule="Plné body do 22 000 Kč." {ontoggle}>
	<span>nastavení</span>
</PreferenceCard>
