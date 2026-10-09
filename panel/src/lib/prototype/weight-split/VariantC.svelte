<!-- PROTOTYPE, throwaway. Variant C, bar as tabs: each segment is a
preference, clicking one opens its settings below, and preferences that are
off wait after the bar as add buttons. -->
<script lang="ts">
	import SettingControl from './SettingControl.svelte';
	import { ICON, rule, SHORT, TITLE, type SplitState, type Wish } from './split.svelte';

	let { split }: { split: SplitState } = $props();

	let bar = $state<HTMLElement>();
	let selected = $state<Wish>('price');

	const off = $derived(split.available.filter((wish) => split.weights[wish] === 0));
	const selectedOn = $derived(split.weights[selected] > 0);
</script>

<div class="c">
	<div class="c__row">
		<div class="c__bar" bind:this={bar}>
			{#each split.on as wish, index (wish)}
				<button
					type="button"
					class="c__segment pref-{wish}"
					class:c__segment--selected={selected === wish}
					style:flex-grow={split.weights[wish]}
					onclick={() => (selected = wish)}
				>
					<span class="c__icon">{ICON[wish]}</span>
					<span class="c__text">
						<span class="c__name">{SHORT[wish]}</span>
						<span class="c__share">{split.weights[wish]} %</span>
					</span>
				</button>
				{#if index < split.on.length - 1}
					<span
						class="c__divider"
						role="slider"
						tabindex="0"
						aria-label="Předěl za {SHORT[wish]}"
						aria-valuenow={split.weights[wish]}
						onpointerdown={(event) => bar && split.drag(index, event, bar)}
						onkeydown={(event) => split.nudge(index, event)}
					></span>
				{/if}
			{/each}
		</div>
		{#if off.length > 0}
			<div class="c__add">
				{#each off as wish (wish)}
					<button
						type="button"
						class="c__add-button"
						class:c__add-button--selected={selected === wish}
						onclick={() => (selected = wish)}>+ {SHORT[wish]}</button
					>
				{/each}
			</div>
		{/if}
	</div>

	<div class="c__panel pref-{selected}" class:c__panel--off={!selectedOn}>
		<div class="c__panel-head">
			<span class="c__panel-icon">{ICON[selected]}</span>
			<div class="c__panel-title">
				<h4>{TITLE[selected]}</h4>
				<small>
					{selectedOn
						? `Rozhoduje ze ${split.weights[selected]} % skóre`
						: split.ready(selected)
							? 'Vypnuto, nerozhoduje'
							: 'Nejdřív nastavte, pak zapněte'}
				</small>
			</div>
			<button
				type="button"
				class="c__toggle"
				class:c__toggle--on={selectedOn}
				disabled={!selectedOn && !split.ready(selected)}
				onclick={() => split.toggle(selected)}>{selectedOn ? 'Vypnout' : 'Zapnout'}</button
			>
		</div>
		<SettingControl {split} wish={selected} />
		<p class="c__rule">{rule(split, selected)}</p>
	</div>
</div>

<style>
	.c {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.c__row {
		display: flex;
		align-items: stretch;
		gap: var(--space-3);
	}

	.c__bar {
		flex: 1;
		display: flex;
		min-width: 0;
		height: 4rem;
		user-select: none;
	}

	.c__segment {
		position: relative;
		display: flex;
		align-items: center;
		gap: var(--space-2);
		flex-basis: 0;
		min-width: 0;
		padding: 0 var(--space-3);
		border: none;
		background: var(--pref);
		color: var(--pref-text);
		text-align: left;
		overflow: hidden;
		cursor: pointer;
		transition: flex-grow 80ms ease-out, transform 120ms ease-out;
	}

	.c__segment:first-child {
		border-radius: var(--radius-md) 0 0 var(--radius-md);
	}

	.c__segment:last-child {
		border-radius: 0 var(--radius-md) var(--radius-md) 0;
	}

	.c__segment--selected {
		box-shadow: inset 0 -4px 0 var(--color-ink);
	}

	.c__icon {
		flex: none;
		display: grid;
		place-items: center;
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 50%;
		background: color-mix(in srgb, var(--pref-text) 18%, transparent);
		font-size: 0.6875rem;
		font-weight: 800;
	}

	.c__text {
		display: flex;
		flex-direction: column;
		min-width: 0;
		line-height: 1.15;
		white-space: nowrap;
	}

	.c__name {
		font-size: 0.75rem;
		font-weight: 600;
		opacity: 0.85;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.c__share {
		font-size: 1.25rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}

	.c__divider {
		position: relative;
		z-index: 1;
		flex: 0 0 3px;
		background: var(--color-ground);
		cursor: col-resize;
		touch-action: none;
	}

	.c__divider::before {
		content: '';
		position: absolute;
		inset: 0 -8px;
	}

	.c__divider::after {
		content: '⋮';
		position: absolute;
		top: 50%;
		left: 50%;
		display: grid;
		place-items: center;
		width: 1.125rem;
		height: 1.75rem;
		border-radius: var(--radius-md);
		background: var(--color-ground);
		color: var(--color-ink);
		font-size: 0.875rem;
		font-weight: 800;
		transform: translate(-50%, -50%);
		box-shadow: 0 1px 3px color-mix(in srgb, var(--color-ink) 25%, transparent);
	}

	.c__divider:focus-visible {
		outline: none;
	}

	.c__divider:focus-visible::after {
		outline: 2px solid var(--color-amber);
	}

	.c__add {
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: var(--space-1);
	}

	.c__add-button {
		padding: var(--space-1) var(--space-3);
		border: 1px dashed var(--color-line);
		border-radius: var(--radius-full);
		background: none;
		color: var(--color-bronze);
		font-size: 0.8125rem;
		white-space: nowrap;
		cursor: pointer;
	}

	.c__add-button--selected {
		border-style: solid;
		border-color: var(--color-ink);
		color: var(--color-ink);
	}

	.c__panel {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		margin-top: var(--space-3);
		padding: var(--space-4);
		border: 1px solid var(--color-line);
		border-top: 4px solid var(--pref);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.c__panel--off {
		border-top-color: var(--color-line);
	}

	.c__panel-head {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.c__panel-icon {
		display: grid;
		place-items: center;
		width: 2.25rem;
		height: 2.25rem;
		border-radius: var(--radius-md);
		background: var(--pref);
		color: var(--pref-text);
		font-size: 0.8125rem;
		font-weight: 800;
	}

	.c__panel--off .c__panel-icon {
		background: var(--color-line);
		color: var(--color-bronze);
	}

	.c__panel-title {
		flex: 1;
	}

	.c__panel-title h4 {
		margin: 0;
		font-size: 1rem;
	}

	.c__panel-title small {
		color: var(--color-bronze);
	}

	.c__toggle {
		padding: var(--space-2) var(--space-4);
		border: none;
		border-radius: var(--radius-md);
		background: var(--color-amber);
		color: var(--color-on-amber);
		font-weight: 700;
		cursor: pointer;
	}

	.c__toggle--on {
		border: 1px solid var(--color-line);
		background: none;
		color: inherit;
		font-weight: 600;
	}

	.c__toggle:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}

	.c__rule {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}
</style>
