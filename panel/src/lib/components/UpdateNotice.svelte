<script lang="ts">
	import { opensInBrowser } from '$lib/browser-link';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { releasePage, type UpdateStore } from '$lib/stores/update.svelte';

	/* The top bar's word that a newer release is out, and the way to install
	it. Shows nothing while the app is up to date. */
	let { updates }: { updates: UpdateStore } = $props();

	const t = getTranslatorContext();
	const state = $derived(updates.state);
</script>

{#if state.status === 'available'}
	<div class="update-notice">
		<span>{t.t('Version {version} is available', { version: state.version })}</span>
		<button type="button" class="update-notice__install" onclick={() => updates.install()}>
			{t.t('Update and restart')}
		</button>
	</div>
{:else if state.status === 'installing'}
	<div class="update-notice" role="status">
		{state.percent === null
			? t.t('Downloading the update...')
			: t.t('Downloading the update... {percent} %', { percent: state.percent })}
	</div>
{:else if state.status === 'failed'}
	<div class="update-notice" role="alert" title={state.error}>
		<span>{t.t('The update could not be installed.')}</span>
		<a class="update-notice__link" href={releasePage(state.version)} use:opensInBrowser>
			{t.t('Download it by hand')}
		</a>
	</div>
{/if}

<style>
	.update-notice {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-1) var(--space-1) var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-ground);
		color: var(--color-bronze);
		font-size: 0.8125rem;
		white-space: nowrap;
	}

	.update-notice__install {
		padding: var(--space-1) var(--space-3);
		border: none;
		border-radius: var(--radius-full);
		background: var(--color-olive);
		color: var(--color-ground);
		font-weight: 600;
		cursor: pointer;
	}

	.update-notice__link {
		padding-right: var(--space-2);
		color: inherit;
		font-weight: 600;
	}
</style>
