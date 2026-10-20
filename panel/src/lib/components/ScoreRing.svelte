<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';

	/* A listing's score out of 100 as a ring filled that far. A coloured ring
	runs from bronze through amber to olive as the score rises, a plain one
	keeps to the ink. It fills the width it is given, its number growing with
	it. */
	let { score, coloured }: { score: number; coloured: boolean } = $props();

	const t = getTranslatorContext();

	const RADIUS = 16;
	const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

	const colour = $derived(ringColour(score, coloured));

	function ringColour(score: number, coloured: boolean): string {
		if (!coloured) return 'var(--color-ink)';
		if (score >= 50) return `color-mix(in oklch, var(--color-olive) ${(score - 50) * 2}%, var(--color-amber))`;
		return `color-mix(in oklch, var(--color-amber) ${score * 2}%, var(--color-bronze))`;
	}
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
		width: 100%;
		aspect-ratio: 1;
		container-type: inline-size;
	}

	.score-ring__svg {
		display: block;
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
		font-size: 30cqi;
		font-weight: 800;
		line-height: 1;
		font-variant-numeric: tabular-nums;
	}
</style>
