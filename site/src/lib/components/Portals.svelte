<script lang="ts">
	import type { Messages } from '$lib/i18n/messages';

	let { t }: { t: Messages } = $props();

	const PORTALS: Array<{ name: string; onByDefault: boolean }> = [
		{ name: 'RE/MAX', onByDefault: true },
		{ name: 'iDNES Reality', onByDefault: true },
		{ name: 'Sreality.cz', onByDefault: false },
		{ name: 'Bezrealitky.cz', onByDefault: false }
	];
</script>

<section class="container" aria-label={t.portals.label}>
	<div class="row">
		<span class="heading">{t.portals.heading}</span>
		<ul>
			{#each PORTALS as portal (portal.name)}
				<li class="portal" class:off={!portal.onByDefault}>
					{#if portal.onByDefault}
						<span class="live" aria-hidden="true"></span>
					{/if}
					{portal.name}
				</li>
			{/each}
			<li><a class="portal portal-more" href="#roadmap">{t.portals.more}</a></li>
		</ul>
	</div>
	<div class="notes">
		<p>{t.portals.defaults}</p>
		<p>{t.portals.notAffiliated}</p>
	</div>
</section>

<style>
	section {
		padding-bottom: 64px;
	}

	.row {
		border-top: 1px solid var(--line);
		padding-top: 28px;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 16px 28px;
	}

	.heading {
		font-size: 13px;
		font-weight: 800;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--muted);
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 12px;
	}

	.portal {
		display: inline-flex;
		align-items: center;
		gap: 10px;
		min-height: 44px;
		padding: 0 18px;
		border: 1px solid var(--line);
		background: var(--surface);
		border-radius: 999px;
		font-weight: 800;
		font-size: 18px;
		letter-spacing: -0.01em;
		color: var(--text);
		box-sizing: border-box;
		text-decoration: none;
	}

	.portal.off {
		background: transparent;
		color: var(--muted);
	}

	.portal-more {
		border-style: dashed;
		border-color: var(--line-strong);
		background: transparent;
		color: var(--muted);
		font-weight: 700;
		font-size: 15px;
	}

	.portal-more:hover {
		color: var(--link);
		border-color: var(--link);
	}

	.notes {
		margin-top: 16px;
		display: flex;
		flex-direction: column;
		gap: 6px;
		max-width: 70ch;
		font-size: 15px;
		line-height: 1.5;
		color: var(--muted);
	}

	.live {
		width: 8px;
		height: 8px;
		border-radius: 999px;
		background: var(--amber);
		animation: live 2.4s infinite;
	}

	@keyframes live {
		0% {
			box-shadow: 0 0 0 0 rgba(220, 133, 31, 0.55);
		}
		70% {
			box-shadow: 0 0 0 9px rgba(220, 133, 31, 0);
		}
		100% {
			box-shadow: 0 0 0 0 rgba(220, 133, 31, 0);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.live {
			animation: none;
		}
	}
</style>
