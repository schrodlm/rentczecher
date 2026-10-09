<script lang="ts">
	import '$lib/styles/preferences.css';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { moveDivider } from './split';
	import type { Weights, Preference } from './preferences';

	/* The counting preferences side by side, each as wide as its weight, with
	a divider between neighbours to drag or nudge with the arrow keys. */
	let {
		weights = $bindable(),
		counting,
		label
	}: { weights: Weights; counting: readonly Preference[]; label: (preference: Preference) => string } = $props();

	const t = getTranslatorContext();

	let bar = $state<HTMLElement>();

	// Measured from where the drag began, so rounding to whole points never
	// piles up while the pointer moves.
	function drag(left: Preference, right: Preference, event: PointerEvent): void {
		if (bar === undefined) return;
		const handle = event.currentTarget as HTMLElement;
		handle.setPointerCapture(event.pointerId);
		const startWeight = weights[left];
		const startX = event.clientX;
		const width = bar.getBoundingClientRect().width;
		function move(moved: PointerEvent): void {
			const target = startWeight + ((moved.clientX - startX) / width) * 100;
			weights = moveDivider(weights, left, right, target - weights[left]);
		}
		function stop(): void {
			handle.removeEventListener('pointermove', move);
			handle.removeEventListener('pointerup', stop);
			handle.removeEventListener('pointercancel', stop);
		}
		handle.addEventListener('pointermove', move);
		handle.addEventListener('pointerup', stop);
		handle.addEventListener('pointercancel', stop);
	}

	function nudge(left: Preference, right: Preference, event: KeyboardEvent): void {
		const step = event.shiftKey ? 5 : 1;
		if (event.key === 'ArrowLeft') weights = moveDivider(weights, left, right, -step);
		else if (event.key === 'ArrowRight') weights = moveDivider(weights, left, right, step);
		else return;
		event.preventDefault();
	}
</script>

<div class="split-bar" bind:this={bar}>
	{#each counting as preference, index (preference)}
		<div class="split-bar__segment preference-{preference}" style:flex-grow={weights[preference]}>
			<span class="split-bar__name">{label(preference)}</span>
			<span class="split-bar__share">{weights[preference]} %</span>
		</div>
		{#if index < counting.length - 1}
			{@const right = counting[index + 1]}
			<button
				type="button"
				class="split-bar__divider"
				role="slider"
				aria-label={t.t('Between {left} and {right}', { left: label(preference), right: label(right) })}
				aria-valuemin={0}
				aria-valuemax={100}
				aria-valuenow={weights[preference]}
				onpointerdown={(event) => drag(preference, right, event)}
				onkeydown={(event) => nudge(preference, right, event)}
			></button>
		{/if}
	{/each}
</div>

<style>
	.split-bar {
		display: flex;
		height: 3.25rem;
		user-select: none;
	}

	.split-bar__segment {
		display: flex;
		flex-direction: column;
		justify-content: center;
		flex-basis: 0;
		min-width: 0;
		padding: 0 var(--space-3);
		overflow: hidden;
		background: var(--preference);
		color: var(--preference-text);
		white-space: nowrap;
	}

	.split-bar__segment:first-child {
		border-radius: var(--radius-md) 0 0 var(--radius-md);
	}

	.split-bar__segment:last-child {
		border-radius: 0 var(--radius-md) var(--radius-md) 0;
	}

	.split-bar__segment:only-child {
		border-radius: var(--radius-md);
	}

	.split-bar__name {
		overflow: hidden;
		font-size: 0.75rem;
		font-weight: 600;
		opacity: 0.85;
		text-overflow: ellipsis;
	}

	.split-bar__share {
		font-size: 1.125rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}

	.split-bar__divider {
		position: relative;
		z-index: 1;
		flex: 0 0 4px;
		padding: 0;
		border: none;
		background: var(--color-ground);
		cursor: col-resize;
		touch-action: none;
	}

	.split-bar__divider::after {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		width: 0.875rem;
		height: 1.75rem;
		border: 2px solid var(--color-ground);
		border-radius: var(--radius-full);
		background: var(--color-ink);
		transform: translate(-50%, -50%);
		transition: transform 80ms ease-out;
	}

	.split-bar__divider:hover::after,
	.split-bar__divider:focus-visible::after {
		transform: translate(-50%, -50%) scale(1.15);
	}

	.split-bar__divider:focus-visible {
		outline: none;
	}

	.split-bar__divider:focus-visible::after {
		outline: 2px solid var(--color-amber);
	}
</style>
