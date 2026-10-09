<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';

	/* A listing's score out of 100 as a ring filled that far, its colour
	running from bronze through amber to olive as the score rises. */
	let { score }: { score: number } = $props();

	const t = getTranslatorContext();

	const RADIUS = 16;
	const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

	const colour = $derived(
		score >= 50
			? `color-mix(in oklch, var(--color-olive) ${(score - 50) * 2}%, var(--color-amber))`
			: `color-mix(in oklch, var(--color-amber) ${score * 2}%, var(--color-bronze))`
	);
</script>

<div class="score-ring" style:--score-colour={colour} role="img" aria-label={t.t('Score {score} of 100', { score })}>
	<svg class="score-ring__svg" viewBox="0 0 40 40" aria-hidden="true">
		<circle class="score-ring__track" cx="20" cy="20" r={RADIUS} />
		<circle
			class="score-ring__fill"
			cx="20"
			cy="20"
			r={RADIUS}
			stroke-dasharray="{(CIRCUMFERENCE * score) / 100} {CIRCUMFERENCE}"
		/>
	</svg>
	<span class="score-ring__number">{score}</span>
</div>

<style>
	.score-ring {
		position: relative;
		flex-shrink: 0;
		width: 3rem;
		height: 3rem;
	}

	.score-ring__svg {
		width: 100%;
		height: 100%;
		transform: rotate(-90deg);
	}

	.score-ring__track,
	.score-ring__fill {
		fill: none;
		stroke-width: 4;
	}

	.score-ring__track {
		stroke: var(--color-line);
	}

	.score-ring__fill {
		stroke: var(--score-colour);
		stroke-linecap: round;
	}

	.score-ring__number {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
		color: var(--color-ink);
		font-size: 0.875rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}
</style>
