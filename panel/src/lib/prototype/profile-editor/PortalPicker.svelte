<!-- PROTOTYPE, throwaway. The portals a profile scans, as logo tiles. The
logos are the portals' own favicons, bundled because the app's content
policy only loads local images. -->
<script lang="ts">
	import sreality from './logos/sreality.svg';
	import bezrealitky from './logos/bezrealitky.svg';
	import remax from './logos/remax.svg';
	import { PORTALS, PORTAL_LABEL, type Portal } from './draft.svelte';

	let { portals = $bindable() }: { portals: Portal[] } = $props();

	const LOGO: Record<Portal, string> = { sreality, bezrealitky, remax };
	const SITE: Record<Portal, string> = { sreality: 'sreality.cz', bezrealitky: 'bezrealitky.cz', remax: 'remax-czech.cz' };

	function toggle(portal: Portal): void {
		portals = portals.includes(portal) ? portals.filter((p) => p !== portal) : [...portals, portal];
	}
</script>

<div class="portals">
	{#each PORTALS as portal (portal)}
		<button type="button" class="tile" class:on={portals.includes(portal)} aria-pressed={portals.includes(portal)} onclick={() => toggle(portal)}>
			<img src={LOGO[portal]} alt="" />
			<span class="tile__name">{PORTAL_LABEL[portal]}</span>
			<span class="tile__site">{SITE[portal]}</span>
			<span class="tile__check">{portals.includes(portal) ? '✓' : ''}</span>
		</button>
	{/each}
</div>
{#if portals.length === 0}<p class="warn">Pick at least one portal.</p>{/if}

<style>
	.portals { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3); }
	.tile { position: relative; display: grid; grid-template-columns: 2.5rem 1fr; grid-template-rows: auto auto; column-gap: var(--space-3); align-items: center; text-align: left; padding: var(--space-3); border: 1px solid var(--color-line); border-radius: var(--radius-md); background: var(--color-card); color: inherit; cursor: pointer; opacity: 0.55; filter: grayscale(1); transition: opacity 120ms, filter 120ms, border-color 120ms; }
	.tile.on { opacity: 1; filter: none; border-color: var(--color-olive); box-shadow: inset 0 0 0 1px var(--color-olive); }
	.tile img { grid-row: span 2; width: 2.5rem; height: 2.5rem; object-fit: contain; }
	.tile__name { font-weight: 700; }
	.tile__site { font-size: 0.75rem; color: var(--color-bronze); }
	.tile__check { position: absolute; top: var(--space-2); right: var(--space-3); color: var(--color-olive); font-weight: 700; }
	.warn { color: var(--color-bronze); font-size: 0.8125rem; margin: var(--space-2) 0 0; }
</style>
