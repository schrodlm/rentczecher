<script lang="ts">
	import { opensInBrowser } from '$lib/browser-link';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { PORTALS, type PortalShown, type Portal } from '$lib/portals';

	/* The portals a profile scans, each a tile with its logo that toggles. A
	portal that asks apps not to read it turns on only after its note is
	confirmed. */
	let { selected = $bindable(), name }: { selected: Portal[]; name: string } = $props();

	const t = getTranslatorContext();
	let confirming = $state<PortalShown | null>(null);

	function toggle(shown: PortalShown): void {
		if (selected.includes(shown.portal)) {
			selected = selected.filter((picked) => picked !== shown.portal);
		} else if (shown.optInTerms !== null) {
			confirming = shown;
		} else {
			selected = [...selected, shown.portal];
		}
	}

	function turnOn(shown: PortalShown): void {
		selected = [...selected, shown.portal];
		confirming = null;
	}
</script>

<div class="portal-tiles" role="group" aria-label={name}>
	{#each PORTALS as shown (shown.portal)}
		<button
			type="button"
			class="portal-tiles__tile"
			class:portal-tiles__tile--on={selected.includes(shown.portal)}
			aria-pressed={selected.includes(shown.portal)}
			onclick={() => toggle(shown)}
		>
			<img class="portal-tiles__logo" src={shown.logo} alt="" />
			<span class="portal-tiles__name">{shown.name}</span>
			<span class="portal-tiles__site">{shown.site}</span>
		</button>
	{/each}
</div>
{#if confirming !== null && confirming.optInTerms !== null}
	{@const asking = confirming}
	<div class="portal-tiles__note" role="group" aria-label={asking.name}>
		<p class="portal-tiles__note-text">
			{t.t(
				"{name} asks that apps like this one don't read its site. If you turn it on, rentczecher reads it only for your own searches, slowly, and stops if {name} says no.",
				{ name: asking.name }
			)}
			<a href={asking.optInTerms} target="_blank" rel="noreferrer" use:opensInBrowser>
				{t.t("{name}'s terms", { name: asking.name })}
			</a>
		</p>
		<div class="portal-tiles__note-actions">
			<button type="button" class="portal-tiles__turn-on" onclick={() => turnOn(asking)}>
				{t.t('Turn on')}
			</button>
			<button type="button" class="portal-tiles__not-now" onclick={() => (confirming = null)}>
				{t.t('Not now')}
			</button>
		</div>
	</div>
{/if}
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
		transition: border-color 120ms;
	}

	.portal-tiles__tile--on {
		border-color: var(--color-olive);
		box-shadow: inset 0 0 0 1px var(--color-olive);
	}

	.portal-tiles__logo {
		grid-row: span 2;
		width: 2.5rem;
		height: 2.5rem;
		object-fit: contain;
		filter: grayscale(1) opacity(0.45);
		transition: filter 120ms;
	}

	.portal-tiles__tile--on .portal-tiles__logo {
		filter: none;
	}

	.portal-tiles__name {
		font-weight: 700;
	}

	.portal-tiles__site {
		font-size: 0.75rem;
		color: var(--color-bronze);
	}

	.portal-tiles__note {
		margin-top: var(--space-3);
		padding: var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.portal-tiles__note-text {
		margin: 0;
		font-size: 0.875rem;
	}

	.portal-tiles__note-text a {
		color: var(--color-bronze);
	}

	.portal-tiles__note-actions {
		display: flex;
		gap: var(--space-3);
		margin-top: var(--space-3);
	}

	.portal-tiles__turn-on {
		padding: var(--space-2) var(--space-4);
		border: 1px solid var(--color-olive);
		border-radius: var(--radius-md);
		background: none;
		color: inherit;
		font-weight: 600;
		cursor: pointer;
	}

	.portal-tiles__not-now {
		padding: var(--space-2) var(--space-4);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: none;
		color: inherit;
		cursor: pointer;
	}

	.portal-tiles__warning {
		margin: var(--space-2) 0 0;
		font-size: 0.8125rem;
		color: var(--color-bronze);
	}
</style>
