<script lang="ts">
	import type { Language } from '$lib/user-config';

	/* The flag a language is picked by, its own colours warmed a little towards
	the palette so it sits in the app without turning into another flag. */
	let { language }: { language: Language } = $props();

	const id = $props.id();
</script>

<svg class="flag" viewBox="0 0 30 20" aria-hidden="true">
	<clipPath id="{id}-round"><rect width="30" height="20" rx="3" /></clipPath>
	{#if language === 'cs'}
		<g clip-path="url(#{id}-round)">
			<rect width="30" height="10" fill="#fbf7ef" />
			<rect y="10" width="30" height="10" fill="#c8402f" />
			<path d="M0 0 15 10 0 20z" fill="#24466f" />
		</g>
	{:else}
		<clipPath id="{id}-quarters"><path d="M15 10h15v10zv10H0zH0V0zV0h15z" /></clipPath>
		<g clip-path="url(#{id}-round)">
			<rect width="30" height="20" fill="#24466f" />
			<path d="M0 0l30 20m0-20L0 20" stroke="#fbf7ef" stroke-width="4" />
			<path d="M0 0l30 20m0-20L0 20" clip-path="url(#{id}-quarters)" stroke="#c8402f" stroke-width="2" />
			<path d="M15 0v20M0 10h30" stroke="#fbf7ef" stroke-width="6" />
			<path d="M15 0v20M0 10h30" stroke="#c8402f" stroke-width="3.5" />
		</g>
	{/if}
	<rect
		x="0.25"
		y="0.25"
		width="29.5"
		height="19.5"
		rx="2.8"
		fill="none"
		stroke="#343330"
		stroke-opacity="0.15"
		stroke-width="0.5"
	/>
</svg>

<style>
	.flag {
		display: block;
		height: 100%;
	}
</style>
