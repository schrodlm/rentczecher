<!-- PROTOTYPE, throwaway. Three variants of setting the scoring weights on a
split bar, switchable via ?variant=A|B|C, inside a mock of the editor's
scoring section with the example listings beside it. -->
<script lang="ts">
	import '$lib/prototype/weight-split/colors.css';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import ExampleCards from '$lib/prototype/weight-split/ExampleCards.svelte';
	import { SplitState } from '$lib/prototype/weight-split/split.svelte';
	import VariantA from '$lib/prototype/weight-split/VariantA.svelte';
	import VariantB from '$lib/prototype/weight-split/VariantB.svelte';
	import VariantC from '$lib/prototype/weight-split/VariantC.svelte';

	const VARIANTS = [
		{ key: 'A', name: 'Header bar' },
		{ key: 'B', name: 'Ruler' },
		{ key: 'C', name: 'Bar as tabs' }
	];

	const split = new SplitState();
	const variant = $derived(page.url.searchParams.get('variant') ?? 'A');
	const current = $derived(VARIANTS.findIndex((v) => v.key === variant));

	function show(by: number): void {
		const next = VARIANTS[(current + by + VARIANTS.length) % VARIANTS.length];
		void goto(`?variant=${next.key}`, { replaceState: true, noScroll: true, keepFocus: true });
	}

	function onkeydown(event: KeyboardEvent): void {
		const target = event.target as HTMLElement;
		if (target.closest('input, textarea, [contenteditable], [role="slider"]')) return;
		if (event.key === 'ArrowLeft') show(-1);
		if (event.key === 'ArrowRight') show(1);
	}
</script>

<svelte:window {onkeydown} />

<div class="proto">
	<div class="proto__window">
		<header class="proto__head">Upravit profil · <b>Praha 7 byty</b></header>
		<div class="proto__body">
			<div class="proto__main">
				{#if variant === 'B'}
					<VariantB {split} />
				{:else if variant === 'C'}
					<VariantC {split} />
				{:else}
					<VariantA {split} />
				{/if}
			</div>
			<ExampleCards {split} />
		</div>
	</div>
	<pre class="proto__state">{JSON.stringify(split.weights)}  ·  součet {split.on.reduce((sum, wish) => sum + split.weights[wish], 0)}</pre>
</div>

<nav class="switcher">
	<button type="button" onclick={() => show(-1)}>←</button>
	<span>{VARIANTS[current]?.key} ({VARIANTS[current]?.name})</span>
	<button type="button" onclick={() => show(1)}>→</button>
</nav>

<style>
	.proto {
		min-height: 100vh;
		padding: var(--space-6) var(--space-6) 6rem;
		background: color-mix(in srgb, var(--color-ink) 45%, var(--color-ground));
	}

	.proto__window {
		max-width: 66rem;
		margin: 0 auto;
		border-radius: 0.75rem;
		background: var(--color-ground);
		box-shadow: 0 24px 64px rgb(0 0 0 / 0.35);
		overflow: hidden;
	}

	.proto__head {
		padding: var(--space-3) var(--space-6);
		border-bottom: 1px solid var(--color-line);
	}

	.proto__body {
		display: grid;
		grid-template-columns: 1fr 18rem;
		gap: var(--space-6);
		align-items: start;
		padding: var(--space-6);
	}

	.proto__main {
		min-width: 0;
	}

	.proto__state {
		max-width: 66rem;
		margin: var(--space-3) auto 0;
		color: var(--color-ground);
		font-size: 0.75rem;
	}

	.switcher {
		position: fixed;
		bottom: 1rem;
		left: 50%;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.4rem 0.75rem;
		border-radius: 999px;
		background: #111;
		color: #fff;
		font: 600 0.8125rem system-ui;
		box-shadow: 0 6px 20px rgb(0 0 0 / 0.4);
		transform: translateX(-50%);
	}

	.switcher button {
		border: none;
		background: #333;
		color: #fff;
		border-radius: 999px;
		width: 1.75rem;
		height: 1.75rem;
		cursor: pointer;
	}
</style>
