<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';

	/* score is nullable: the API carries no score field, a listing's score
	is an in-memory pipeline annotation. The ring renders nothing without
	one. */
	let { score }: { score: number | null } = $props();

	const t = getTranslatorContext();

	const band = $derived(score === null ? null : score >= 70 ? 'high' : score >= 40 ? 'mid' : 'low');
	const circumference = 2 * Math.PI * 15.5;
	const dashoffset = $derived(score === null ? circumference : circumference * (1 - score / 100));
</script>

{#if score !== null}
	<div class="ring ring--{band}" title={t.t('Score {score}', { score })}>
		<svg viewBox="0 0 36 36" width="36" height="36">
			<circle class="ring__track" cx="18" cy="18" r="15.5" fill="none" stroke-width="3" />
			<circle
				class="ring__value"
				cx="18"
				cy="18"
				r="15.5"
				fill="none"
				stroke-width="3"
				stroke-dasharray={circumference}
				stroke-dashoffset={dashoffset}
				transform="rotate(-90 18 18)"
			/>
		</svg>
		<span class="ring__number">{score}</span>
	</div>
{/if}

<style>
	.ring {
		position: relative;
		width: 36px;
		height: 36px;
	}

	.ring__track {
		stroke: var(--color-line);
	}

	.ring--high .ring__value {
		stroke: var(--color-olive);
	}

	.ring--mid .ring__value {
		stroke: var(--color-bronze);
	}

	.ring--low .ring__value {
		stroke: var(--color-line);
	}

	.ring__number {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.6875rem;
		font-weight: 600;
		color: var(--color-ink);
	}
</style>
