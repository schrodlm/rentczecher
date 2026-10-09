<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { PORTALS, type Portal } from '$lib/portals';

	/* The portals a profile scans, each a tile with its logo that toggles. */
	let { selected = $bindable(), name }: { selected: Portal[]; name: string } = $props();

	const t = getTranslatorContext();

	function toggle(portal: Portal): void {
		selected = selected.includes(portal) ? selected.filter((picked) => picked !== portal) : [...selected, portal];
	}
</script>

<div class="portal-tiles" role="group" aria-label={name}>
	{#each PORTALS as shown (shown.portal)}
		<button
			type="button"
			class="portal-tiles__tile"
			class:portal-tiles__tile--on={selected.includes(shown.portal)}
			aria-pressed={selected.includes(shown.portal)}
			onclick={() => toggle(shown.portal)}
		>
			<img class="portal-tiles__logo" src={shown.logo} alt="" />
			<span class="portal-tiles__name">{shown.name}</span>
			<span class="portal-tiles__site">{shown.site}</span>
		</button>
	{/each}
</div>
{#if selected.length === 0}
	<p class="portal-tiles__warning">{t.t('Pick at least one portal.')}</p>
{/if}

<style>
	.portal-tiles {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: var(--space-3);
	}

	.portal-tiles__tile {
		display: grid;
		grid-template-columns: 2.5rem 1fr;
		grid-template-rows: auto auto;
		column-gap: var(--space-3);
		align-items: center;
		padding: var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
		color: inherit;
		text-align: left;
		cursor: pointer;
		opacity: 0.55;
		filter: grayscale(1);
		transition:
			opacity 120ms,
			filter 120ms,
			border-color 120ms;
	}

	.portal-tiles__tile--on {
		opacity: 1;
		filter: none;
		border-color: var(--color-olive);
		box-shadow: inset 0 0 0 1px var(--color-olive);
	}

	.portal-tiles__logo {
		grid-row: span 2;
		width: 2.5rem;
		height: 2.5rem;
		object-fit: contain;
	}

	.portal-tiles__name {
		font-weight: 700;
	}

	.portal-tiles__site {
		font-size: 0.75rem;
		color: var(--color-bronze);
	}

	.portal-tiles__warning {
		margin: var(--space-2) 0 0;
		font-size: 0.8125rem;
		color: var(--color-bronze);
	}
</style>
