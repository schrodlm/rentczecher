<script lang="ts">
	import { onMount } from 'svelte';
	import { opensInBrowser } from '$lib/browser-link';
	import { getTranslatorContext } from '$lib/i18n/context';

	/* One photo over the whole window, stepped with the arrows and closed
	with Escape. The corner names the portal the photos come from and links
	to the posting. */
	let {
		photos,
		current = $bindable(),
		downloading,
		portalName,
		postingUrl,
		onclose
	}: {
		photos: readonly string[];
		current: number;
		downloading: boolean;
		portalName: string;
		postingUrl: string;
		onclose: () => void;
	} = $props();

	const t = getTranslatorContext();

	let viewer = $state<HTMLElement>();

	function step(by: number): void {
		current = (current + by + photos.length) % photos.length;
	}

	function onkeydown(event: KeyboardEvent): void {
		if (event.defaultPrevented) return;
		if (event.key === 'ArrowLeft') step(-1);
		else if (event.key === 'ArrowRight') step(1);
		else if (event.key === 'Escape') onclose();
		else return;
		event.preventDefault();
	}

	// The viewer takes the focus while open and hands it back on closing.
	onMount(() => {
		const opener = document.activeElement;
		viewer?.focus();
		return () => {
			if (opener instanceof HTMLElement) opener.focus();
		};
	});
</script>

<svelte:window {onkeydown} />

<div class="photo-viewer" role="dialog" aria-modal="true" aria-label={t.t('Photos')} tabindex="-1" bind:this={viewer}>
	<button type="button" class="photo-viewer__close" aria-label={t.t('Close')} onclick={onclose}>×</button>
	<img class="photo-viewer__photo" src={photos[current]} alt="" />
	{#if photos.length > 1}
		<button
			type="button"
			class="photo-viewer__step photo-viewer__step--previous"
			aria-label={t.t('Previous photo')}
			onclick={() => step(-1)}>‹</button
		>
		<button
			type="button"
			class="photo-viewer__step photo-viewer__step--next"
			aria-label={t.t('Next photo')}
			onclick={() => step(1)}>›</button
		>
	{/if}
	<div class="photo-viewer__foot">
		<span>
			{current + 1} / {photos.length}
			{#if downloading}<span class="photo-viewer__downloading">{t.t('Downloading more photos…')}</span>{/if}
		</span>
		<a href={postingUrl} target="_blank" rel="noopener noreferrer" use:opensInBrowser>
			{t.t('Photos: {portal}', { portal: portalName })} ↗
		</a>
	</div>
</div>

<style>
	.photo-viewer {
		position: fixed;
		inset: 0;
		z-index: 60;
		display: grid;
		place-items: center;
		background: rgb(16 15 14 / 92%);
	}

	.photo-viewer:focus {
		outline: none;
	}

	.photo-viewer__photo {
		max-width: calc(100vw - 9rem);
		max-height: calc(100vh - 6rem);
		object-fit: contain;
		border-radius: var(--radius-sm);
		box-shadow: 0 16px 48px rgb(0 0 0 / 50%);
	}

	.photo-viewer__close {
		position: absolute;
		top: var(--space-3);
		right: var(--space-4);
		border: none;
		background: none;
		color: #f3ede2;
		font-size: 2rem;
		cursor: pointer;
	}

	.photo-viewer__step {
		position: absolute;
		top: 50%;
		width: 3rem;
		height: 3rem;
		border: none;
		border-radius: var(--radius-full);
		background: rgb(255 255 255 / 12%);
		color: #f3ede2;
		font-size: 1.75rem;
		transform: translateY(-50%);
		cursor: pointer;
	}

	.photo-viewer__step:hover {
		background: rgb(255 255 255 / 22%);
	}

	.photo-viewer__step--previous {
		left: var(--space-4);
	}

	.photo-viewer__step--next {
		right: var(--space-4);
	}

	.photo-viewer__foot {
		position: absolute;
		right: var(--space-4);
		bottom: var(--space-3);
		left: var(--space-4);
		display: flex;
		justify-content: space-between;
		color: #f3ede2;
		font-size: 0.875rem;
	}

	.photo-viewer__downloading {
		margin-left: var(--space-3);
		opacity: 0.75;
		animation: photo-viewer-breathe 2.8s ease-in-out infinite;
	}

	@keyframes photo-viewer-breathe {
		50% {
			opacity: 0.4;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.photo-viewer__downloading {
			animation: none;
		}
	}

	.photo-viewer__foot a {
		color: var(--color-amber-bright);
		text-decoration: none;
	}
</style>
