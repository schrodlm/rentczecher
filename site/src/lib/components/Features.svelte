<script lang="ts">
	import FeatureIllustration, { type FeatureIllustrationKind } from './FeatureIllustration.svelte';
	import type { FeatureCard, Messages } from '$lib/i18n/messages';

	let { t }: { t: Messages } = $props();

	const cards: Array<{ kind: FeatureIllustrationKind; copy: FeatureCard }> = $derived([
		{ kind: 'onlyNew', copy: t.features.cards.onlyNew },
		{ kind: 'oneList', copy: t.features.cards.oneList },
		{ kind: 'memory', copy: t.features.cards.memory },
		{ kind: 'backToPortal', copy: t.features.cards.backToPortal },
		{ kind: 'privacy', copy: t.features.cards.privacy },
		{ kind: 'free', copy: t.features.cards.free }
	]);
</script>

<section id="features" class="band-surface">
	<div class="container inner">
		<div class="head">
			<h2 class="section-heading">{t.features.heading}</h2>
			<p class="section-intro">{t.features.intro}</p>
		</div>
		<div class="grid">
			{#each cards as card (card.kind)}
				<article>
					<div class="art"><FeatureIllustration kind={card.kind} /></div>
					<h3>{card.copy.title}</h3>
					<p>{card.copy.body}</p>
				</article>
			{/each}
		</div>
	</div>
</section>

<style>
	.inner {
		padding-top: 80px;
		padding-bottom: 80px;
		display: flex;
		flex-direction: column;
		gap: 36px;
	}

	.head {
		display: flex;
		flex-direction: column;
		gap: 12px;
		max-width: 40em;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
		gap: 20px;
	}

	article {
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: 14px;
		padding: 16px 16px 22px;
		display: flex;
		flex-direction: column;
		gap: 12px;
		transition:
			transform 0.25s,
			box-shadow 0.25s;
	}

	article:hover {
		transform: translateY(-3px);
		box-shadow: 0 12px 28px var(--shadow);
	}

	article > h3,
	article > p {
		padding: 0 6px;
	}

	.art {
		background: var(--bg);
		border-radius: 10px;
		padding: 18px;
		display: flex;
		justify-content: center;
	}

	h3 {
		font-size: 21px;
	}

	p {
		line-height: 1.5;
		color: var(--muted);
	}

	@media (prefers-reduced-motion: reduce) {
		article {
			transition: none;
		}
	}
</style>
