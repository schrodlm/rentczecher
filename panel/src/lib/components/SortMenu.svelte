<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { naturalOrder, type ListingOrder, type SortField } from '$lib/listing-order';

	/* What the listings are ordered by, picked from a menu, and an arrow that
	turns the order around. */
	let { order = $bindable(), fields }: { order: ListingOrder; fields: readonly SortField[] } = $props();

	const t = getTranslatorContext();
	const menuId = $props.id();

	let open = $state(false);
	let menu = $state<HTMLElement>();

	function fieldName(field: SortField): string {
		if (field === 'score') return t.t('Score');
		if (field === 'date') return t.t('Date');
		if (field === 'price') return t.t('Price');
		if (field === 'pricePerM2') return t.t('Price per m²');
		return t.t('Size');
	}

	function choose(field: SortField): void {
		order = naturalOrder(field);
		open = false;
	}

	function turnAround(): void {
		order = { field: order.field, descending: !order.descending };
	}

	function onwindowclick(event: MouseEvent): void {
		if (open && menu !== undefined && !menu.contains(event.target as Node)) open = false;
	}

	function onkeydown(event: KeyboardEvent): void {
		if (open && event.key === 'Escape') {
			// Only closes the menu, so a window around it stays open.
			event.preventDefault();
			open = false;
		}
	}
</script>

<svelte:window onclick={onwindowclick} {onkeydown} />

<div class="sort-menu" bind:this={menu}>
	<button
		type="button"
		class="sort-menu__field"
		aria-label={t.t('Sort by: {field}', { field: fieldName(order.field) })}
		aria-haspopup="menu"
		aria-expanded={open}
		aria-controls={menuId}
		onclick={() => (open = !open)}
	>
		{fieldName(order.field)}
	</button>
	<button
		type="button"
		class="sort-menu__direction"
		aria-label={order.descending ? t.t('Descending') : t.t('Ascending')}
		onclick={turnAround}
	>
		<svg class="sort-menu__arrow" class:sort-menu__arrow--up={!order.descending} viewBox="0 0 16 16" aria-hidden="true">
			<path d="M8 2.5v11M3.5 9 8 13.5 12.5 9" />
		</svg>
	</button>
	{#if open}
		<ul class="sort-menu__list" id={menuId} role="menu">
			{#each fields as field (field)}
				<li role="none">
					<button
						type="button"
						class="sort-menu__option"
						class:sort-menu__option--chosen={field === order.field}
						role="menuitemradio"
						aria-checked={field === order.field}
						onclick={() => choose(field)}
					>
						<span class="sort-menu__tick" aria-hidden="true">{field === order.field ? '✓' : ''}</span>
						{fieldName(field)}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.sort-menu {
		position: relative;
		display: inline-flex;
	}

	.sort-menu__field,
	.sort-menu__direction {
		display: inline-flex;
		align-items: center;
		padding: var(--space-1) var(--space-2);
		border: 1px solid var(--color-line);
		background: var(--color-card);
		color: var(--color-bronze);
		font-size: 0.8125rem;
		cursor: pointer;
	}

	.sort-menu__field {
		border-radius: var(--radius-full) 0 0 var(--radius-full);
	}

	.sort-menu__direction {
		margin-left: -1px;
		border-radius: 0 var(--radius-full) var(--radius-full) 0;
	}

	.sort-menu__field:hover,
	.sort-menu__direction:hover {
		position: relative;
		border-color: var(--color-bronze);
	}

	.sort-menu__arrow {
		width: 0.875rem;
		height: 0.875rem;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.75;
		stroke-linecap: round;
		stroke-linejoin: round;
		transition: transform 120ms ease-out;
	}

	.sort-menu__arrow--up {
		transform: rotate(180deg);
	}

	.sort-menu__list {
		position: absolute;
		top: calc(100% + var(--space-1));
		right: 0;
		z-index: 10;
		min-width: 12rem;
		margin: 0;
		padding: var(--space-1);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
		box-shadow: 0 6px 20px color-mix(in srgb, var(--color-olive) 20%, transparent);
		list-style: none;
	}

	.sort-menu__option {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-2);
		border: none;
		border-radius: var(--radius-sm);
		background: none;
		color: var(--color-ink);
		font-size: 0.875rem;
		text-align: left;
		cursor: pointer;
	}

	.sort-menu__option:hover {
		background: var(--color-ground);
	}

	.sort-menu__option--chosen {
		font-weight: 700;
	}

	.sort-menu__tick {
		width: 1rem;
		color: var(--color-olive);
	}
</style>
