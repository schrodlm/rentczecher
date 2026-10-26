<script lang="ts">
	import { onMount } from 'svelte';
	import { errorMessage } from '$lib/errors';
	import { appDetails, Feedback, MESSAGE_MAX_LENGTH, openLogFolder, type AppDetails } from '$lib/feedback';
	import { getTranslatorContext } from '$lib/i18n/context';

	/* The window in front of the inbox where a user writes to the author and
	picks how to send it. Sending only opens a draft in their mail client or
	browser. The window stays open with the message, since the shell cannot
	tell whether a draft really appeared. */
	let { onclose }: { onclose: () => void } = $props();

	const t = getTranslatorContext();

	let dialog = $state<HTMLElement>();
	let message = $state('');
	let details = $state<AppDetails | null>(null);
	let status = $state('');
	let busy = $state(false);

	const feedback = $derived(details === null ? null : new Feedback(message, details));
	const canSend = $derived(feedback !== null && message.trim() !== '' && !busy);

	async function attempt(action: () => Promise<void>, done: string, failed: (reason: string) => string): Promise<void> {
		busy = true;
		status = '';
		try {
			await action();
			status = done;
		} catch (error) {
			status = failed(errorMessage(error));
		} finally {
			busy = false;
		}
	}

	function send(open: (feedback: Feedback) => Promise<void>, done: string): Promise<void> {
		const ready = feedback;
		if (ready === null) return Promise.resolve();
		return attempt(
			() => open(ready),
			done,
			(reason) => t.t('Could not open the draft: {reason}', { reason })
		);
	}

	function showLogFile(): Promise<void> {
		return attempt(openLogFolder, '', (reason) => t.t('Could not open the log folder: {reason}', { reason }));
	}

	// A message is never thrown away by a stray click beside the window.
	function closeFromBackdrop(): void {
		if (message.trim() === '') onclose();
	}

	function onkeydown(event: KeyboardEvent): void {
		if (event.key !== 'Escape' || event.defaultPrevented || event.isComposing) return;
		event.preventDefault();
		onclose();
	}

	onMount(() => {
		dialog?.focus();
		void attempt(
			async () => {
				details = await appDetails();
			},
			'',
			(reason) => t.t('Could not read the app version: {reason}', { reason })
		);
	});
</script>

<svelte:window {onkeydown} />

<div class="feedback__backdrop" role="presentation" onclick={closeFromBackdrop}></div>

<div class="feedback" role="dialog" aria-modal="true" aria-labelledby="feedback-title" tabindex="-1" bind:this={dialog}>
	<header class="feedback__head">
		<h2 class="feedback__title" id="feedback-title">{t.t('Send feedback')}</h2>
		<button type="button" class="feedback__close" aria-label={t.t('Close')} onclick={onclose}>×</button>
	</header>

	<div class="feedback__body">
		<label class="feedback__message">
			<span>{t.t('A bug, an idea, anything at all.')}</span>
			<textarea bind:value={message} rows="8" maxlength={MESSAGE_MAX_LENGTH}></textarea>
		</label>
		{#if feedback !== null}
			<p class="feedback__note">{t.t('Sent along: {details}', { details: feedback.detailsLine })}</p>
		{/if}
		<p class="feedback__note">
			{t.t('Something broke? Attach the log file to your message.')}
			<button type="button" class="feedback__link" onclick={showLogFile}>{t.t('Show log file')}</button>
		</p>
	</div>

	<footer class="feedback__foot">
		<span class="feedback__status" role="status">{status}</span>
		<button type="button" class="feedback__ghost" onclick={onclose}>{t.t('Close')}</button>
		<button
			type="button"
			class="feedback__ghost"
			disabled={!canSend}
			onclick={() => send((each) => each.sendAsIssue(), t.t('The issue opened in your browser.'))}
		>
			{t.t('Open GitHub issue')}
		</button>
		<button
			type="button"
			class="feedback__send"
			disabled={!canSend}
			onclick={() =>
				send((each) => each.sendByEmail(t.t('rentczecher feedback')), t.t('The email opened in your mail client.'))}
		>
			{t.t('Send by email')}
		</button>
	</footer>
</div>

<style>
	.feedback__backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		background: color-mix(in srgb, var(--color-ground) 70%, transparent);
		backdrop-filter: blur(2px);
	}

	.feedback {
		position: fixed;
		top: 12vh;
		left: 50%;
		z-index: 41;
		display: flex;
		flex-direction: column;
		width: min(36rem, 94vw);
		overflow: hidden;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-ground);
		box-shadow: 0 24px 64px color-mix(in srgb, var(--color-olive) 25%, transparent);
		transform: translateX(-50%);
	}

	/* The window takes focus when it opens, to bring the keyboard into it,
	without a ring around all of it. */
	.feedback:focus {
		outline: none;
	}

	.feedback__head {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-6);
		border-bottom: 1px solid var(--color-line);
	}

	.feedback__title {
		flex: 1;
		margin: 0;
		font-size: 1.125rem;
	}

	.feedback__close {
		border: none;
		background: none;
		color: var(--color-bronze);
		font-size: 1.5rem;
		cursor: pointer;
	}

	.feedback__body {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-4) var(--space-6);
	}

	.feedback__message {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.feedback__message textarea {
		resize: vertical;
		padding: var(--space-2);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
		color: inherit;
		font: inherit;
	}

	.feedback__note {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.875rem;
	}

	.feedback__link {
		padding: 0;
		border: none;
		background: none;
		color: inherit;
		font: inherit;
		text-decoration: underline;
		cursor: pointer;
	}

	.feedback__foot {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-6);
		border-top: 1px solid var(--color-line);
		background: var(--color-card);
	}

	.feedback__status {
		flex: 1;
		color: var(--color-bronze);
		font-size: 0.875rem;
		text-align: right;
	}

	.feedback__ghost {
		padding: var(--space-2) var(--space-4);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: none;
		color: inherit;
		cursor: pointer;
	}

	.feedback__send {
		padding: var(--space-2) var(--space-6);
		border: none;
		border-radius: var(--radius-md);
		background: var(--color-amber);
		color: var(--color-on-amber);
		font-weight: 700;
		cursor: pointer;
	}

	.feedback__send:disabled,
	.feedback__ghost:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
</style>
