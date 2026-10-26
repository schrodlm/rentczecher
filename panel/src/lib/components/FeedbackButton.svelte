<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';

	/* The top bar's way to the feedback window. */
	let { onclick }: { onclick: () => void } = $props();

	const t = getTranslatorContext();
</script>

<button type="button" class="feedback-button" title={t.t('Send feedback')} aria-label={t.t('Send feedback')} {onclick}>
	<svg viewBox="0 0 24 24" aria-hidden="true">
		<path d="M4 5h16v11H9l-5 4z" />
	</svg>
</button>

<style>
	.feedback-button {
		display: grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		padding: 0;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-ground);
		color: var(--color-ink);
		cursor: pointer;
	}

	.feedback-button:hover {
		border-color: var(--color-bronze);
	}

	.feedback-button svg {
		width: 1rem;
		height: 1rem;
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linejoin: round;
	}
</style>
