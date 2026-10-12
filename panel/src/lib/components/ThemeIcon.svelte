<script lang="ts">
	import type { Theme } from '$lib/user-config';

	/* A sun for light, a moon for dark, a half-filled circle for following
	the system. */
	let { theme }: { theme: Theme } = $props();

	const SUN_RAYS = [0, 45, 90, 135, 180, 225, 270, 315];
</script>

<svg class="theme-icon" viewBox="0 0 20 20" aria-hidden="true">
	{#if theme === 'light'}
		<circle cx="10" cy="10" r="3.6" fill="currentColor" />
		{#each SUN_RAYS as angle (angle)}
			<line
				x1="10"
				y1="2.2"
				x2="10"
				y2="4.4"
				stroke="currentColor"
				stroke-width="1.6"
				stroke-linecap="round"
				transform="rotate({angle} 10 10)"
			/>
		{/each}
	{:else if theme === 'dark'}
		<path d="M16.5 12.2A6.8 6.8 0 1 1 7.8 3.5a5.4 5.4 0 0 0 8.7 8.7z" fill="currentColor" />
	{:else}
		<circle cx="10" cy="10" r="6.4" fill="none" stroke="currentColor" stroke-width="1.6" />
		<path d="M10 3.6a6.4 6.4 0 0 1 0 12.8z" fill="currentColor" />
	{/if}
</svg>

<style>
	.theme-icon {
		width: 1.1em;
		height: 1.1em;
	}
</style>
