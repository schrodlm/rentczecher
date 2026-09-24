<script lang="ts">
	let { source }: { source: string } = $props();

	const letter = $derived(source.charAt(0).toUpperCase());
</script>

<span class="chip">
	<span class="chip__letter">{letter}</span>
	{source}
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
