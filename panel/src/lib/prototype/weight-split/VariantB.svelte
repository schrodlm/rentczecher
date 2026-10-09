<!-- PROTOTYPE, throwaway. Variant B, ruler: a slim track with round knobs and
the shares above it, chips switch preferences on and off, and the cards
below hold only the settings. -->
<script lang="ts">
	import SettingControl from './SettingControl.svelte';
	import { ICON, rule, SHORT, TITLE, type SplitState } from './split.svelte';

	let { split }: { split: SplitState } = $props();

	let track = $state<HTMLElement>();

	/* Where each preference that is on starts and ends along the track. */
	const spans = $derived.by(() => {
		let start = 0;
		return split.on.map((wish) => {
			const span = { wish, start, end: start + split.weights[wish] };
			start = span.end;
			return span;
		});
	});
</script>

<div class="b">
	<div class="b__chips" role="group" aria-label="Co má rozhodovat">
		<span class="b__chips-label">Rozhoduje</span>
		{#each split.available as wish (wish)}
			{@const on = split.weights[wish] > 0}
			<button
				type="button"
				class="b__chip pref-{wish}"
				class:b__chip--on={on}
				aria-pressed={on}
				disabled={!on && !split.ready(wish)}
				title={!on && !split.ready(wish) ? 'Nejdřív nastavte níže' : ''}
				onclick={() => split.toggle(wish)}
			>
				<i class="b__dot"></i>{SHORT[wish]}
			</button>
		{/each}
	</div>

	<div class="b__ruler">
		<div class="b__labels">
			{#each spans as span (span.wish)}
				<span class="b__label" style:left="{(span.start + span.end) / 2}%">
					<b>{split.weights[span.wish]} %</b>
					<small>{SHORT[span.wish]}</small>
				</span>
			{/each}
		</div>
		<div class="b__track" bind:this={track}>
			{#each spans as span (span.wish)}
				<i class="b__fill pref-{span.wish}" style:flex-grow={split.weights[span.wish]}></i>
			{/each}
			{#each spans.slice(0, -1) as span, index (span.wish)}
				<button
					type="button"
					class="b__knob"
					role="slider"
					aria-label="Předěl za {SHORT[span.wish]}"
					aria-valuenow={split.weights[span.wish]}
					style:left="{span.end}%"
					onpointerdown={(event) => track && split.drag(index, event, track)}
					onkeydown={(event) => split.nudge(index, event)}
				></button>
			{/each}
		</div>
		<div class="b__scale"><span>0</span><span>50</span><span>100</span></div>
	</div>

	<div class="b__settings">
		{#each split.available as wish (wish)}
			{@const on = split.weights[wish] > 0}
			<section class="b__setting pref-{wish}" class:b__setting--off={!on}>
				<h4 class="b__setting-title"><span class="b__icon">{ICON[wish]}</span>{TITLE[wish]}</h4>
				<SettingControl {split} {wish} />
				<p class="b__rule">{rule(split, wish)}</p>
			</section>
		{/each}
	</div>
</div>

<style>
	.b {
		display: flex;
		flex-direction: column;
		gap: var(--space-5, 1.25rem);
	}

	.b__chips {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-2);
	}

	.b__chips-label {
		margin-right: var(--space-1);
		color: var(--color-bronze);
		font-size: 0.8125rem;
		font-weight: 600;
	}

	.b__chip {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		color: inherit;
		font-size: 0.8125rem;
		cursor: pointer;
	}

	.b__chip--on {
		border-color: var(--pref);
		background: color-mix(in srgb, var(--pref) 14%, var(--color-card));
		font-weight: 600;
	}

	.b__chip:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}

	.b__dot {
		width: 0.625rem;
		height: 0.625rem;
		border-radius: 50%;
		border: 2px solid var(--pref);
	}

	.b__chip--on .b__dot {
		background: var(--pref);
	}

	.b__ruler {
		padding: 0 var(--space-2);
	}

	.b__labels {
		position: relative;
		height: 2.5rem;
	}

	.b__label {
		position: absolute;
		bottom: var(--space-1);
		display: flex;
		flex-direction: column;
		align-items: center;
		transform: translateX(-50%);
		line-height: 1.1;
		white-space: nowrap;
		transition: left 80ms ease-out;
	}

	.b__label b {
		font-size: 1rem;
		font-variant-numeric: tabular-nums;
	}

	.b__label small {
		color: var(--color-bronze);
		font-size: 0.6875rem;
	}

	.b__track {
		position: relative;
		display: flex;
		height: 0.625rem;
		border-radius: var(--radius-full);
		overflow: visible;
		user-select: none;
	}

	.b__fill {
		flex-basis: 0;
		background: var(--pref);
	}

	.b__fill:first-child {
		border-radius: var(--radius-full) 0 0 var(--radius-full);
	}

	.b__fill:nth-last-child(1 of .b__fill) {
		border-radius: 0 var(--radius-full) var(--radius-full) 0;
	}

	.b__knob {
		position: absolute;
		top: 50%;
		width: 1.375rem;
		height: 1.375rem;
		padding: 0;
		border: 3px solid var(--color-ink);
		border-radius: 50%;
		background: var(--color-card);
		box-shadow: 0 1px 4px color-mix(in srgb, var(--color-ink) 30%, transparent);
		transform: translate(-50%, -50%);
		cursor: grab;
		touch-action: none;
	}

	.b__knob:active {
		cursor: grabbing;
	}

	.b__knob:focus-visible {
		outline: 3px solid color-mix(in srgb, var(--color-amber) 60%, transparent);
	}

	.b__scale {
		display: flex;
		justify-content: space-between;
		margin-top: var(--space-2);
		color: var(--color-bronze);
		font-size: 0.6875rem;
	}

	.b__settings {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-4) var(--space-6);
	}

	.b__setting {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.b__setting--off .b__setting-title {
		color: var(--color-bronze);
	}

	.b__setting-title {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin: 0;
		font-size: 0.9375rem;
	}

	.b__icon {
		display: inline-grid;
		place-items: center;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: var(--radius-md);
		background: var(--pref);
		color: var(--pref-text);
		font-size: 0.6875rem;
		font-weight: 800;
	}

	.b__setting--off .b__icon {
		background: var(--color-line);
		color: var(--color-bronze);
	}

	.b__rule {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}
</style>
