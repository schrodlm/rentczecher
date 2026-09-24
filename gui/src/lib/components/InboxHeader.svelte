<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import PortalHealthDot from './PortalHealthDot.svelte';
	import type { components } from '$lib/api/types.gen';
	import type { RunState } from '$lib/stores/run-progress.svelte';

	type PortalHealthModel = components['schemas']['PortalHealthModel'];

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
			return runState.error !== null
				? t.t('Scan failed: {error}', { error: runState.error })
				: t.t('Scan failed');
		}
		if (lastFinishedAt !== null) {
			return t.t('Last scan: {time}', { time: lastFinishedAt.toLocaleTimeString('cs-CZ') });
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
		gap: var(--space-3);
	}

	.actions__health {
		display: inline-flex;
		gap: var(--space-1);
	}

	.actions__status {
		font-size: 0.8125rem;
		color: var(--color-bronze);
		white-space: nowrap;
	}

	.actions__run {
		background: var(--color-amber);
		color: var(--color-on-amber);
		border: none;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-4);
		font-weight: 600;
		cursor: pointer;
	}

	.actions__run:hover:enabled {
		background: var(--color-amber-bright);
	}

	.actions__run:disabled {
		opacity: 0.6;
		cursor: default;
	}
</style>
