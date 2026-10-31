<script lang="ts">
	import { onMount } from 'svelte';
	import type { ProfileModel } from '$lib/api/client';
	import { errorMessage } from '$lib/errors';
	import { getTranslatorContext } from '$lib/i18n/context';

	/* The window where a user picks which profiles to save into a file, every
	one picked at first. onexport resolves false when the user closed the
	save dialog without saving, and the window then stays open. */
	let {
		profiles,
		onexport,
		onclose
	}: {
		profiles: readonly ProfileModel[];
		onexport: (chosen: ProfileModel[]) => Promise<boolean>;
		onclose: () => void;
	} = $props();

	const t = getTranslatorContext();

	let dialog = $state<HTMLElement>();
	// svelte-ignore state_referenced_locally
	let chosenIds = $state<string[]>(profiles.map((profile) => profile.id));
	let status = $state('');
	let busy = $state(false);

	const chosen = $derived(profiles.filter((profile) => chosenIds.includes(profile.id)));

	function toggle(profileId: string): void {
		chosenIds = chosenIds.includes(profileId)
			? chosenIds.filter((each) => each !== profileId)
			: [...chosenIds, profileId];
	}

	async function exportChosen(): Promise<void> {
		busy = true;
		status = '';
		let saved: boolean;
		try {
			saved = await onexport(chosen);
		} catch (error) {
			status = t.t('Could not save the file: {reason}', { reason: errorMessage(error) });
			return;
		} finally {
			busy = false;
		}
		if (saved) onclose();
	}

	// Not while the save dialog is open, which would save from a closed window.
	function close(): void {
		if (!busy) onclose();
	}

	function onkeydown(event: KeyboardEvent): void {
		if (event.key !== 'Escape' || event.defaultPrevented || event.isComposing) return;
		event.preventDefault();
		close();
	}

	onMount(() => dialog?.focus());
</script>

<svelte:window {onkeydown} />

<div class="export__backdrop" role="presentation" onclick={close}></div>

<div class="export" role="dialog" aria-modal="true" aria-labelledby="export-title" tabindex="-1" bind:this={dialog}>
	<header class="export__head">
		<h2 class="export__title" id="export-title">{t.t('Export profiles')}</h2>
		<button type="button" class="export__close" aria-label={t.t('Close')} onclick={close}>×</button>
	</header>

	<div class="export__body">
		<p class="export__note">
			{t.t('The file holds the chosen searches and their preferences, not the listings they found.')}
		</p>
		<ul class="export__list">
			{#each profiles as profile (profile.id)}
				<li>
					<label class="export__profile">
						<input
							type="checkbox"
							checked={chosenIds.includes(profile.id)}
							onchange={() => toggle(profile.id)}
						/>
						{profile.name}
					</label>
				</li>
			{/each}
		</ul>
	</div>

	<footer class="export__foot">
		<span class="export__status" role="status">{status}</span>
		<button type="button" class="export__ghost" onclick={close}>{t.t('Cancel')}</button>
		<button type="button" class="export__save" disabled={chosen.length === 0 || busy} onclick={exportChosen}>
			{t.t('Export')}
		</button>
	</footer>
</div>

<style>
	.export__backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		background: color-mix(in srgb, var(--color-ground) 70%, transparent);
		backdrop-filter: blur(2px);
	}

	.export {
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

	.export:focus {
		outline: none;
	}

	.export__head {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-6);
		border-bottom: 1px solid var(--color-line);
	}

	.export__title {
		flex: 1;
		margin: 0;
		font-size: 1.125rem;
	}

	.export__close {
		border: none;
		background: none;
		color: var(--color-bronze);
		font-size: 1.5rem;
		cursor: pointer;
	}

	.export__body {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
		overflow-y: auto;
	}

	.export__note {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.875rem;
	}

	.export__list {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.export__profile {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		cursor: pointer;
	}

	.export__foot {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-6);
		border-top: 1px solid var(--color-line);
		background: var(--color-card);
	}

	.export__status {
		flex: 1;
		color: var(--color-bronze);
		font-size: 0.875rem;
	}

	.export__ghost {
		padding: var(--space-2) var(--space-4);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: none;
		color: inherit;
		cursor: pointer;
	}

	.export__save {
		padding: var(--space-2) var(--space-6);
		border: none;
		border-radius: var(--radius-md);
		background: var(--color-amber);
		color: var(--color-on-amber);
		font-weight: 700;
		cursor: pointer;
	}

	.export__save:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
</style>
