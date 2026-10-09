<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { parseTypedNumber, type Scale } from './scale';

	/* A range with a handle at each end and its two numbers typed beside it.
	A handle at the end of the scale, or an empty box, is no bound on that
	side. A typed number is kept as typed, its handle goes to the nearest
	position. */
	let {
		scale,
		low = $bindable(),
		high = $bindable(),
		name,
		unit
	}: {
		scale: Scale;
		low: number | null;
		high: number | null;
		name: string;
		unit: string;
	} = $props();

	const t = getTranslatorContext();

	const lowIndex = $derived(low === null ? 0 : scale.nearestIndex(low));
	const highIndex = $derived(high === null ? scale.lastIndex : scale.nearestIndex(high));

	// Thousands spaced the Czech way, which parseTypedNumber reads back.
	function written(bound: number | null): string {
		return bound === null ? '' : bound.toLocaleString('cs-CZ');
	}

	function slideLow(index: number): void {
		const kept = Math.min(index, highIndex);
		low = kept === 0 ? null : scale.valueAt(kept);
	}

	function slideHigh(index: number): void {
		const kept = Math.max(index, lowIndex);
		high = kept === scale.lastIndex ? null : scale.valueAt(kept);
	}
</script>

<div class="range-slider">
	<div class="range-slider__track">
		<div
			class="range-slider__fill"
			style:left="{(lowIndex / scale.lastIndex) * 100}%"
			style:width="{((highIndex - lowIndex) / scale.lastIndex) * 100}%"
		></div>
		<input
			type="range"
			class="range-slider__handle"
			min="0"
			max={scale.lastIndex}
			value={lowIndex}
			aria-label={t.t('{name} from', { name })}
			oninput={(event) => slideLow(Number(event.currentTarget.value))}
		/>
		<input
			type="range"
			class="range-slider__handle"
			min="0"
			max={scale.lastIndex}
			value={highIndex}
			aria-label={t.t('{name} to', { name })}
			oninput={(event) => slideHigh(Number(event.currentTarget.value))}
		/>
	</div>
	<div class="range-slider__numbers">
		<input
			class="range-slider__number"
			inputmode="numeric"
			placeholder="0"
			aria-label={t.t('{name} from', { name })}
			value={written(low)}
			onchange={(event) => (low = parseTypedNumber(event.currentTarget.value))}
		/>
		<span>{t.t('to')}</span>
		<input
			class="range-slider__number"
			inputmode="numeric"
			placeholder={t.t('no limit')}
			aria-label={t.t('{name} to', { name })}
			value={written(high)}
			onchange={(event) => (high = parseTypedNumber(event.currentTarget.value))}
		/>
		<span class="range-slider__unit">{unit}</span>
	</div>
</div>

<style>
	.range-slider {
		display: grid;
		grid-template-columns: 1fr auto;
		align-items: center;
		gap: var(--space-3);
	}

	.range-slider__track {
		position: relative;
		height: 1.5rem;
	}

	.range-slider__track::before,
	.range-slider__fill {
		position: absolute;
		top: 50%;
		height: 4px;
		margin-top: -2px;
		border-radius: 2px;
	}

	.range-slider__track::before {
		content: '';
		left: 0;
		right: 0;
		background: var(--color-line);
	}

	.range-slider__fill {
		background: var(--color-olive);
	}

	/* Two range inputs share the track. Only their thumbs take the pointer,
	so either handle can be grabbed. */
	.range-slider__handle {
		position: absolute;
		inset: 0;
		width: 100%;
		margin: 0;
		background: none;
		pointer-events: none;
		appearance: none;
		-webkit-appearance: none;
	}

	.range-slider__handle::-webkit-slider-runnable-track {
		background: none;
	}

	.range-slider__handle::-moz-range-track {
		background: none;
	}

	.range-slider__handle::-webkit-slider-thumb {
		pointer-events: auto;
		-webkit-appearance: none;
		width: 1.1rem;
		height: 1.1rem;
		border-radius: 50%;
		background: var(--color-card);
		border: 2px solid var(--color-olive);
		cursor: grab;
	}

	.range-slider__handle::-moz-range-thumb {
		pointer-events: auto;
		width: 1rem;
		height: 1rem;
		border-radius: 50%;
		background: var(--color-card);
		border: 2px solid var(--color-olive);
		cursor: grab;
	}

	.range-slider__numbers {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		font-size: 0.8125rem;
		color: var(--color-bronze);
	}

	.range-slider__number {
		width: 6.5rem;
		padding: var(--space-1) var(--space-2);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
		color: var(--color-ink);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}

	.range-slider__unit {
		min-width: 1.75rem;
	}
</style>
