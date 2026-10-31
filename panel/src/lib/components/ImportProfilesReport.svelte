<script lang="ts">
	import { onMount } from 'svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import type { ImportReport } from '$lib/import-profiles';

	/* The window that tells how importing a file of profiles went: which
	profiles it added, and which the engine refused, with the reason on hover. */
	let { report, onclose }: { report: ImportReport; onclose: () => void } = $props();

	const t = getTranslatorContext();

	let dialog = $state<HTMLElement>();

	function onkeydown(event: KeyboardEvent): void {
		if (event.key !== 'Escape' || event.defaultPrevented || event.isComposing) return;
		event.preventDefault();
		onclose();
	}

	onMount(() => dialog?.focus());
</script>

<svelte:window {onkeydown} />

<div class="import__backdrop" role="presentation" onclick={onclose}></div>

<div class="import" role="dialog" aria-modal="true" aria-labelledby="import-title" tabindex="-1" bind:this={dialog}>
	<header class="import__head">
		<h2 class="import__title" id="import-title">{t.t('Import profiles')}</h2>
		<button type="button" class="import__close" aria-label={t.t('Close')} onclick={onclose}>×</button>
	</header>

	<div class="import__body">
		{#if report.status === 'unreadable'}
			<p role="alert">{t.t('This file holds no profiles rentczecher can read.')}</p>
		{:else if report.status === 'failed'}
			<p role="alert">{t.t('Could not read the file: {reason}', { reason: report.reason })}</p>
		{:else}
			{@const { added, refused } = report.outcome}
			{#if added.length > 0}
				<p>{t.tn('Added {count} profile:', 'Added {count} profiles:', added.length)}</p>
				<ul class="import__list">
					{#each added as profile (profile.id)}
						<li>{profile.name}</li>
					{/each}
				</ul>
			{:else if refused.length === 0}
				<p>{t.t('The file holds no profiles.')}</p>
			{/if}
			{#if refused.length > 0}
				<p role="alert">{t.tn('{count} profile could not be added:', '{count} profiles could not be added:', refused.length)}</p>
				<ul class="import__list">
					{#each refused as profile}
						<li title={profile.reason}>{profile.name}</li>
					{/each}
				</ul>
			{/if}
		{/if}
	</div>

	<footer class="import__foot">
		<button type="button" class="import__ok" onclick={onclose}>{t.t('Close')}</button>
	</footer>
</div>

<style>
	.import__backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		background: color-mix(in srgb, var(--color-ground) 70%, transparent);
		backdrop-filter: blur(2px);
	}

	.import {
		position: fixed;
		top: 12vh;
		left: 50%;
		z-index: 41;
		display: flex;
		flex-direction: column;
		width: min(28rem, 94vw);
		max-height: 76vh;
		overflow: hidden;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-ground);
		box-shadow: 0 24px 64px color-mix(in srgb, var(--color-olive) 25%, transparent);
		transform: translateX(-50%);
	}

	.import:focus {
		outline: none;
	}

	.import__head {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-6);
		border-bottom: 1px solid var(--color-line);
	}

	.import__title {
		flex: 1;
		margin: 0;
		font-size: 1.125rem;
	}

	.import__close {
		border: none;
		background: none;
		color: var(--color-bronze);
		font-size: 1.5rem;
		cursor: pointer;
	}

	.import__body {
		padding: var(--space-4) var(--space-6);
		overflow-y: auto;
	}

	.import__body p {
		margin: 0 0 var(--space-2);
	}

	.import__list {
		margin: 0 0 var(--space-3);
		padding-left: var(--space-6);
	}

	.import__foot {
		display: flex;
		justify-content: flex-end;
		padding: var(--space-3) var(--space-6);
		border-top: 1px solid var(--color-line);
		background: var(--color-card);
	}

	.import__ok {
		padding: var(--space-2) var(--space-6);
		border: none;
		border-radius: var(--radius-md);
		background: var(--color-amber);
		color: var(--color-on-amber);
		font-weight: 700;
		cursor: pointer;
	}
</style>
