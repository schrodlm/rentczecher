<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import PortalHealthDot from './PortalHealthDot.svelte';
	import type { PortalHealthModel } from '$lib/api/client';
	import type { RunState } from '$lib/stores/run-progress.svelte';
	import { shownPortal } from '$lib/portals';

	let {
		health,
		runState,
		lastFinishedAt,
		triggerError,
		onrun
	}: {
		health: PortalHealthModel[];
		runState: RunState;
		lastFinishedAt: Date | null;
		triggerError: string | null;
		onrun: () => void;
	} = $props();

	const t = getTranslatorContext();

	const isRunning = $derived(runState.status === 'running');

	// One line of truth beside the button, most urgent state first.
	const statusLabel = $derived.by(() => {
		if (triggerError !== null) {
			return t.t('Scan failed: {error}', { error: triggerError });
		}
		if (runState.status === 'running') {
			return t.tn('{count} portal done', '{count} portals done', runState.scrapersDone.length);
		}
		if (runState.status === 'failed') {
			if (runState.error !== null) {
				return t.t('Scan failed: {error}', { error: runState.error });
			}
			return runState.noPortalAnswered
				? t.t('Scan failed: no portal could be reached. Check your internet connection.')
				: t.t('Scan failed');
		}
		if (lastFinishedAt !== null) {
			if (runState.status === 'done' && runState.brokenPortals.length > 0) {
				const portals = runState.brokenPortals
					.map((portal) => shownPortal(portal)?.name ?? portal)
					.join(', ');
				return t.t('Last scan: {time}, unreachable: {portals}', {
					time: t.time(lastFinishedAt),
					portals
				});
			}
			return t.t('Last scan: {time}', { time: t.time(lastFinishedAt) });
		}
		return t.t('No scan yet');
	});
</script>

<div class="actions">
	<span class="actions__health">
		{#each health as entry (entry.portal)}
			<PortalHealthDot portal={entry.portal} status={entry.status} />
		{/each}
	</span>
	<span class="actions__status">{statusLabel}</span>
	<button type="button" class="actions__run" disabled={isRunning} onclick={onrun}>
		{isRunning ? t.t('Scan running...') : t.t('Run scan')}
	</button>
</div>

<style>
	.actions {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.actions__health {
		display: inline-flex;
		gap: var(--space-2);
	}

	.actions__status {
		font-size: 0.875rem;
		color: var(--color-bronze);
		white-space: nowrap;
	}

	/* The app's main action, so it stands up off the bar in a glow of its
	own colour. */
	.actions__run {
		background: var(--color-amber);
		color: var(--color-on-amber);
		border: none;
		border-radius: var(--radius-md);
		padding: 0.625rem 1.25rem;
		font-size: 0.9375rem;
		font-weight: 700;
		box-shadow:
			0 4px 14px color-mix(in srgb, var(--color-amber) 45%, transparent),
			0 1px 2px rgb(0 0 0 / 20%);
		cursor: pointer;
		transition:
			transform 0.15s ease,
			box-shadow 0.15s ease,
			background 0.15s ease;
	}

	.actions__run:hover:enabled {
		background: var(--color-amber-bright);
		box-shadow:
			0 6px 20px color-mix(in srgb, var(--color-amber) 55%, transparent),
			0 2px 4px rgb(0 0 0 / 20%);
		transform: translateY(-1px);
	}

	.actions__run:active:enabled {
		box-shadow:
			0 2px 8px color-mix(in srgb, var(--color-amber) 40%, transparent),
			0 1px 2px rgb(0 0 0 / 20%);
		transform: translateY(0);
	}

	.actions__run:disabled {
		opacity: 0.6;
		box-shadow: none;
		cursor: default;
	}

	@media (prefers-reduced-motion: reduce) {
		.actions__run {
			transition: none;
		}
	}
</style>
