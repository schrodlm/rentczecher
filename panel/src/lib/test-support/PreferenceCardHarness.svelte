<script lang="ts">
	import PreferenceCard from '$lib/scoring/PreferenceCard.svelte';

	/* Renders a PreferenceCard with a stand-in setting inside it. */
	let { share }: { share: number | null } = $props();
</script>

<PreferenceCard preference="price" title="Preferovaná cena" {share} rule="Plné body do 22 000 Kč.">
	<span>nastavení</span>
</PreferenceCard>
