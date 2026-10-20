<script lang="ts">
	import { onMount } from 'svelte';
	import type { components } from '$lib/api/types.gen';
	import { getTranslatorContext } from '$lib/i18n/context';
	import StreetMap from './StreetMap.svelte';
	import StreetMapCredit from './StreetMapCredit.svelte';

	type PointModel = components['schemas']['PointModel'];

	/* The street map over the whole window, closed with Escape. */
	let { point, onclose }: { point: PointModel; onclose: () => void } = $props();

	const t = getTranslatorContext();

	let window_ = $state<HTMLElement>();

	function onkeydown(event: KeyboardEvent): void {
		if (event.defaultPrevented || event.key !== 'Escape') return;
		event.preventDefault();
		onclose();
	}

	// The window takes the focus while open and hands it back on closing.
	onMount(() => {
		const opener = document.activeElement;
		window_?.focus();
		return () => {
			if (opener instanceof HTMLElement) opener.focus();
		};
	});
</script>

<svelte:window {onkeydown} />

<div class="street-map-window" role="dialog" aria-modal="true" aria-label={t.t('Map')} tabindex="-1" bind:this={window_}>
	<div class="street-map-window__map"><StreetMap {point} wholeWindow={true} /></div>
	<button type="button" class="street-map-window__close" aria-label={t.t('Close')} onclick={onclose}>×</button>
	<div class="street-map-window__credit"><StreetMapCredit /></div>
</div>

<style>
	.street-map-window {
		position: fixed;
		inset: 0;
		z-index: 60;
		padding: var(--space-6);
		background: rgb(16 15 14 / 92%);
	}

	.street-map-window:focus {
		outline: none;
	}

	.street-map-window__map {
		height: 100%;
	}

	.street-map-window__close {
		position: absolute;
		top: var(--space-1);
		right: var(--space-2);
		border: none;
		background: none;
		color: #f3ede2;
		font-size: 2rem;
		cursor: pointer;
	}

	.street-map-window__credit {
		position: absolute;
		right: var(--space-6);
		bottom: var(--space-1);
	}
</style>
