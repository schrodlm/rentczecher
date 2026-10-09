<script lang="ts">
	import { sourceInitial } from '$lib/format';
	import { shownPortal } from '$lib/portals';

	/* The portal a listing came from: its logo and name, or its first letter
	for a source the panel does not know. */
	let { source }: { source: string } = $props();

	const portal = $derived(shownPortal(source));
</script>

<span class="chip">
	{#if portal}
		<img class="chip__logo" src={portal.logo} alt="" />
		{portal.name}
	{:else}
		<span class="chip__letter">{sourceInitial(source)}</span>
		{source}
	{/if}
</span>

<style>
	.chip {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-2);
		border-radius: var(--radius-full);
		border: 1px solid var(--color-line);
		font-size: 0.75rem;
		color: var(--color-ink);
	}

	.chip__logo {
		width: 1.125rem;
		height: 1.125rem;
		object-fit: contain;
	}

	.chip__letter {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.125rem;
		height: 1.125rem;
		border-radius: var(--radius-full);
		background: var(--color-line);
		font-weight: 600;
		font-size: 0.625rem;
	}
</style>
