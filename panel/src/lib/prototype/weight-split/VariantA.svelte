<!-- PROTOTYPE, throwaway. Variant A, header bar: one big labelled bar above
the preference cards, each card switched on or off and striped in its colour. -->
<script lang="ts">
	import SettingControl from './SettingControl.svelte';
	import { rule, SHORT, TITLE, type SplitState } from './split.svelte';

	let { split }: { split: SplitState } = $props();

	let bar = $state<HTMLElement>();
</script>

<div class="a">
	<div class="a__head">
		<h3 class="a__title">Co je pro vás nejdůležitější?</h3>
		<p class="a__hint">Táhněte předěly v pruhu. Čím širší díl, tím víc preference rozhoduje o pořadí.</p>
	</div>

	{#if split.on.length > 0}
		<div class="a__bar" bind:this={bar}>
			{#each split.on as wish, index (wish)}
				<div class="a__segment pref-{wish}" style:flex-grow={split.weights[wish]}>
					<span class="a__name">{SHORT[wish]}</span>
					<span class="a__share">{split.weights[wish]} %</span>
				</div>
				{#if index < split.on.length - 1}
					<button
						type="button"
						class="a__divider"
						role="slider"
						aria-label="Předěl mezi {SHORT[wish]} a {SHORT[split.on[index + 1]]}"
						aria-valuenow={split.weights[wish]}
						onpointerdown={(event) => bar && split.drag(index, event, bar)}
						onkeydown={(event) => split.nudge(index, event)}
					></button>
				{/if}
			{/each}
		</div>
	{:else}
		<div class="a__bar a__bar--empty">Zapněte aspoň jednu preferenci. Do té doby se inzeráty řadí od nejnovějších.</div>
	{/if}

	<div class="a__cards">
		{#each split.available as wish (wish)}
			{@const on = split.weights[wish] > 0}
			<div class="a__card pref-{wish}" class:a__card--off={!on}>
				<div class="a__card-head">
					<button
						type="button"
						class="a__switch"
						class:a__switch--on={on}
						role="switch"
						aria-checked={on}
						aria-label={TITLE[wish]}
						disabled={!on && !split.ready(wish)}
						onclick={() => split.toggle(wish)}
					><i></i></button>
					<strong class="a__card-title">{TITLE[wish]}</strong>
					{#if on}<span class="a__badge">{split.weights[wish]} %</span>{/if}
				</div>
				<SettingControl {split} {wish} />
				<p class="a__rule">{rule(split, wish)}</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.a {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.a__title {
		margin: 0;
		font-size: 1.0625rem;
	}

	.a__hint {
		margin: var(--space-1) 0 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	.a__bar {
		display: flex;
		height: 3.25rem;
		border-radius: var(--radius-md);
		background: var(--color-line);
		user-select: none;
	}

	.a__bar--empty {
		align-items: center;
		justify-content: center;
		color: var(--color-bronze);
		font-size: 0.8125rem;
		border: 1px dashed var(--color-line);
		background: none;
	}

	.a__segment {
		display: flex;
		flex-direction: column;
		justify-content: center;
		min-width: 0;
		flex-basis: 0;
		padding: 0 var(--space-3);
		background: var(--pref);
		color: var(--pref-text);
		overflow: hidden;
		white-space: nowrap;
		transition: flex-grow 80ms ease-out;
	}

	.a__segment:first-child {
		border-radius: var(--radius-md) 0 0 var(--radius-md);
	}

	.a__segment:last-child {
		border-radius: 0 var(--radius-md) var(--radius-md) 0;
	}

	.a__name {
		font-size: 0.75rem;
		font-weight: 600;
		opacity: 0.85;
		text-overflow: ellipsis;
		overflow: hidden;
	}

	.a__share {
		font-size: 1.125rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}

	.a__divider {
		position: relative;
		z-index: 1;
		flex: 0 0 4px;
		padding: 0;
		border: none;
		background: var(--color-ground);
		cursor: col-resize;
		touch-action: none;
	}

	.a__divider::after {
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

	.a__divider:hover::after,
	.a__divider:focus-visible::after {
		transform: translate(-50%, -50%) scale(1.15);
	}

	.a__divider:focus-visible {
		outline: none;
	}

	.a__cards {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-3);
	}

	.a__card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-3) var(--space-3) var(--space-4);
		border: 1px solid var(--color-line);
		border-left: 4px solid var(--pref);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.a__card--off {
		border-left-color: var(--color-line);
		background: var(--color-ground);
	}

	.a__card--off .a__card-title {
		color: var(--color-bronze);
	}

	.a__card-head {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.a__card-title {
		flex: 1;
	}

	.a__badge {
		padding: 0 var(--space-2);
		border-radius: var(--radius-full);
		background: var(--pref);
		color: var(--pref-text);
		font-size: 0.75rem;
		font-weight: 700;
	}

	.a__switch {
		position: relative;
		width: 2.25rem;
		height: 1.25rem;
		padding: 0;
		border: none;
		border-radius: var(--radius-full);
		background: var(--color-line);
		cursor: pointer;
	}

	.a__switch i {
		position: absolute;
		top: 2px;
		left: 2px;
		width: calc(1.25rem - 4px);
		height: calc(1.25rem - 4px);
		border-radius: 50%;
		background: var(--color-card);
		transition: left 120ms ease-out;
	}

	.a__switch--on {
		background: var(--color-olive);
	}

	.a__switch--on i {
		left: calc(100% - 1.25rem + 2px);
	}

	.a__switch:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.a__rule {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}
</style>
