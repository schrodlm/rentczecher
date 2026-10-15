<script lang="ts">
	import CzechMap from './CzechMap.svelte';
	import Icon from './Icon.svelte';
	import PinShape from './PinShape.svelte';
	import type { Messages } from '$lib/i18n/messages';
	import { REPO_URL } from '$lib/links';

	let { t, appVersion }: { t: Messages; appVersion: string } = $props();
</script>

<section class="container hero">
	<div class="pitch">
		<a class="badge" href={REPO_URL}>
			<Icon name="code" size={16} />
			{t.hero.badge}
		</a>
		<h1>
			{t.hero.lead}<span class="visually-hidden">{t.hero.kindsLabel}</span><span class="swap" aria-hidden="true"
				>{#each t.hero.kinds as kind (kind)}<span>{kind}</span>{/each}</span
			>{t.hero.tail}<br />
			<span class="promise">{t.hero.promise}</span>
		</h1>
		<p class="intro">{t.hero.intro}</p>
		<div class="actions">
			<div class="buttons">
				<a class="btn btn-amber" href="#download">
					<Icon name="download" />
					{t.hero.download}
				</a>
				<a class="btn btn-line" href={REPO_URL}>
					<Icon name="star" />
					{t.hero.source}
				</a>
			</div>
			<span class="fineprint">{t.hero.freeVersion(appVersion)} {t.hero.platforms}</span>
		</div>
	</div>

	<div>
		<CzechMap label={t.hero.mapLabel} />
		<div class="listings">
			<div class="listing">
				<div class="listing-head">
					<span class="tag tag-new">{t.hero.newBadge}</span>
					<span class="ago">{t.hero.newAgo}</span>
				</div>
				<div class="listing-title">
					<svg class="mini" width="16" height="16" viewBox="-15 -29 30 31" aria-hidden="true"><PinShape kind="flat" /></svg>
					{t.hero.newTitle}
				</div>
				<div class="listing-detail">{t.hero.newDetail}</div>
			</div>
			<div class="listing">
				<div class="listing-head">
					<span class="tag tag-drop">{t.hero.dropBadge}</span>
					<span class="ago">{t.hero.dropAgo}</span>
				</div>
				<div class="listing-title">
					<svg class="mini" width="16" height="16" viewBox="-15 -29 30 31" aria-hidden="true"><PinShape kind="cottage" /></svg>
					{t.hero.dropTitle}
				</div>
				<div class="listing-detail">
					{t.hero.dropDetail} <span class="drop-amount">{t.hero.dropAmount}</span>
				</div>
			</div>
		</div>
	</div>
</section>

<style>
	.hero {
		padding-top: 40px;
		padding-bottom: 72px;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
		gap: 48px;
		align-items: center;
	}

	.pitch {
		display: flex;
		flex-direction: column;
		gap: 26px;
	}

	.badge {
		align-self: flex-start;
		display: inline-flex;
		align-items: center;
		gap: 8px;
		border: 1px solid var(--line-strong);
		border-radius: 999px;
		padding: 6px 14px;
		font-size: 14px;
		color: var(--text);
		text-decoration: none;
	}

	h1 {
		font-size: clamp(40px, 5.4vw, 64px);
		line-height: 1.08;
		letter-spacing: -0.025em;
		font-weight: 800;
	}

	.promise {
		color: var(--olive);
	}

	.swap {
		display: inline-grid;
		color: var(--link);
		text-decoration: underline;
		text-decoration-color: var(--amber);
		text-decoration-thickness: 0.1em;
		text-underline-offset: 0.16em;
	}

	.swap > span {
		grid-area: 1 / 1;
		opacity: 0;
		animation: swap 9s infinite;
	}

	.swap > span:nth-child(2) {
		animation-delay: 3s;
	}

	.swap > span:nth-child(3) {
		animation-delay: 6s;
	}

	@keyframes swap {
		0% {
			opacity: 0;
			transform: translateY(0.3em);
		}
		4%,
		30% {
			opacity: 1;
			transform: none;
		}
		34%,
		100% {
			opacity: 0;
			transform: translateY(-0.3em);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.swap > span {
			animation: none;
		}

		.swap > span:first-child {
			opacity: 1;
		}
	}

	.intro {
		font-size: 19px;
		line-height: 1.55;
		max-width: 34em;
	}

	.actions {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 12px;
	}

	.buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
	}

	.fineprint {
		font-size: 14px;
		color: var(--muted);
	}

	.listings {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
		gap: 12px;
		margin-top: 8px;
	}

	.listing {
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: 8px;
		padding: 12px 14px;
		display: flex;
		flex-direction: column;
		gap: 4px;
		box-shadow: 0 6px 18px var(--shadow);
	}

	.listing-head {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.tag {
		font-size: 11px;
		font-weight: 800;
		letter-spacing: 0.06em;
		padding: 2px 8px;
		border-radius: 999px;
	}

	.tag-new {
		background: var(--amber);
		color: var(--on-amber);
	}

	.tag-drop {
		background: var(--olive);
		color: var(--on-olive);
	}

	.ago {
		font-size: 12px;
		color: var(--muted);
	}

	.listing-title {
		font-weight: 700;
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.mini {
		fill: var(--amber);
	}

	.mini :global(rect) {
		fill: var(--on-amber);
	}

	.listing-detail {
		font-size: 14px;
		color: var(--muted);
	}

	.drop-amount {
		color: var(--olive);
		font-weight: 700;
	}
</style>
