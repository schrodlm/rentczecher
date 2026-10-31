<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';

	/* The menu beside the profile tabs that moves profiles in and out of the
	app through a file. Export needs a profile to export. */
	let {
		canExport,
		onimport,
		onexport
	}: { canExport: boolean; onimport: () => void; onexport: () => void } = $props();

	const t = getTranslatorContext();
	const menuId = $props.id();

	let open = $state(false);
	let menu = $state<HTMLElement>();

	function choose(action: () => void): void {
		open = false;
		action();
	}

	function onwindowclick(event: MouseEvent): void {
		if (open && menu !== undefined && !menu.contains(event.target as Node)) open = false;
	}

	function onkeydown(event: KeyboardEvent): void {
		if (open && event.key === 'Escape') {
			event.preventDefault();
			open = false;
		}
	}
</script>

<svelte:window onclick={onwindowclick} {onkeydown} />

<div class="profiles-menu" bind:this={menu}>
	<button
		type="button"
		class="profiles-menu__toggle"
		title={t.t('More profile actions')}
		aria-label={t.t('More profile actions')}
		aria-haspopup="menu"
		aria-expanded={open}
		aria-controls={menuId}
		onclick={() => (open = !open)}
	>
		⋯
	</button>
	{#if open}
		<ul class="profiles-menu__list" id={menuId} role="menu">
			<li role="none">
				<button type="button" class="profiles-menu__option" role="menuitem" onclick={() => choose(onimport)}>
					{t.t('Import profiles...')}
				</button>
			</li>
			<li role="none">
				<button
					type="button"
					class="profiles-menu__option"
					role="menuitem"
					disabled={!canExport}
					onclick={() => choose(onexport)}
				>
					{t.t('Export profiles...')}
				</button>
			</li>
		</ul>
	{/if}
</div>

<style>
	.profiles-menu {
		position: relative;
		display: inline-flex;
		align-self: center;
	}

	.profiles-menu__toggle {
		display: grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		border: none;
		border-radius: var(--radius-full);
		background: none;
		color: var(--color-bronze);
		font-size: 1.25rem;
		line-height: 1;
		cursor: pointer;
	}

	.profiles-menu__toggle:hover {
		background: var(--color-card);
	}

	.profiles-menu__list {
		position: absolute;
		top: calc(100% + var(--space-1));
		left: 0;
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

	.profiles-menu__option {
		display: block;
		width: 100%;
		padding: var(--space-2);
		border: none;
		border-radius: var(--radius-sm);
		background: none;
		color: var(--color-ink);
		font-size: 0.875rem;
		text-align: left;
		white-space: nowrap;
		cursor: pointer;
	}

	.profiles-menu__option:hover:not(:disabled) {
		background: var(--color-ground);
	}

	.profiles-menu__option:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
</style>
