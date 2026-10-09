<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { layoutName, layoutsByRooms, type Layout } from '$lib/layouts';

	/* The layouts a search accepts, each a chip that toggles, those of one
	room count joined side by side. None picked accepts any layout. */
	let { selected = $bindable(), name }: { selected: Layout[]; name: string } = $props();

	const t = getTranslatorContext();
	const groups = layoutsByRooms();

	function toggle(layout: Layout): void {
		selected = selected.includes(layout) ? selected.filter((picked) => picked !== layout) : [...selected, layout];
	}
</script>

<div class="layout-chips" role="group" aria-label={name}>
	{#each groups as group (group[0])}
		<span class="layout-chips__group">
			{#each group as layout (layout)}
				<button
					type="button"
					class="layout-chips__chip"
					class:layout-chips__chip--on={selected.includes(layout)}
					aria-pressed={selected.includes(layout)}
					onclick={() => toggle(layout)}>{layoutName(layout, t)}</button
				>
			{/each}
		</span>
	{/each}
</div>

<style>
	.layout-chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
	}

	.layout-chips__group {
		display: inline-flex;
	}

	.layout-chips__chip {
		min-width: 2.75rem;
		padding: var(--space-1) var(--space-2);
		margin-left: -1px;
		border: 1px solid var(--color-line);
		background: var(--color-card);
		color: inherit;
		font-size: 0.8125rem;
		cursor: pointer;
	}

	.layout-chips__chip:first-child {
		margin-left: 0;
		border-radius: var(--radius-full) 0 0 var(--radius-full);
	}

	.layout-chips__chip:last-child {
		border-radius: 0 var(--radius-full) var(--radius-full) 0;
	}

	.layout-chips__chip:only-child {
		border-radius: var(--radius-full);
	}

	.layout-chips__chip--on {
		position: relative;
		background: var(--color-olive);
		border-color: var(--color-olive);
		color: var(--color-ground);
	}
</style>
