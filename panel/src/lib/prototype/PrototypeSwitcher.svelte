<!-- PROTOTYPE, throwaway. Floating bar that cycles a ?<param>= on the current
URL. Never rendered in production builds. -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	let {
		variants,
		labels,
		param = 'variant'
	}: { variants: string[]; labels: Record<string, string>; param?: string } = $props();

	const current = $derived(page.url.searchParams.get(param) ?? variants[0]);

	function go(step: number): void {
		const index = (variants.indexOf(current) + step + variants.length) % variants.length;
		const url = new URL(page.url);
		url.searchParams.set(param, variants[index]);
		void goto(url, { replaceState: true, keepFocus: true, noScroll: true });
	}

	function onkeydown(event: KeyboardEvent): void {
		const target = event.target as HTMLElement | null;
		if (target?.closest('input, textarea, select, [contenteditable]')) return;
		if (event.key === 'ArrowLeft') go(-1);
		if (event.key === 'ArrowRight') go(1);
	}
</script>

<svelte:window {onkeydown} />

{#if import.meta.env.DEV}
	<div class="switcher">
		<button type="button" onclick={() => go(-1)}>←</button>
		<span>Map {current}: {labels[current]}</span>
		<button type="button" onclick={() => go(1)}>→</button>
	</div>
{/if}

<style>
	.switcher {
		position: fixed;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 100;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.4rem 0.9rem;
		border-radius: 999px;
		background: #111;
		color: #fff;
		font: 600 0.8125rem system-ui, sans-serif;
		box-shadow: 0 6px 20px rgb(0 0 0 / 0.35);
	}
	.switcher button {
		background: #333;
		color: #fff;
		border: none;
		border-radius: 999px;
		width: 1.75rem;
		height: 1.75rem;
		cursor: pointer;
	}
</style>
