<script lang="ts">
	import '$lib/styles/slider.css';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { parseTypedNumber, writeTypedNumber, type Scale } from './scale';

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

	function slideLow(index: number): void {
		const kept = Math.min(index, highIndex);
		low = kept === 0 ? null : scale.valueAt(kept);
	}

	function slideHigh(index: number): void {
		const kept = Math.max(index, lowIndex);
		high = kept === scale.lastIndex ? null : scale.valueAt(kept);
	}
</script>

<div class="slider">
	<div class="slider__track">
		<div
			class="slider__fill"
			style:left="{(lowIndex / scale.lastIndex) * 100}%"
			style:width="{((highIndex - lowIndex) / scale.lastIndex) * 100}%"
		></div>
		<input
			type="range"
			class="slider__handle"
			min="0"
			max={scale.lastIndex}
			value={lowIndex}
			aria-label={t.t('{name} from', { name })}
			oninput={(event) => slideLow(Number(event.currentTarget.value))}
		/>
		<input
			type="range"
			class="slider__handle"
			min="0"
			max={scale.lastIndex}
			value={highIndex}
			aria-label={t.t('{name} to', { name })}
			oninput={(event) => slideHigh(Number(event.currentTarget.value))}
		/>
	</div>
	<div class="slider__numbers">
		<input
			class="slider__number"
			inputmode="numeric"
			placeholder="0"
			aria-label={t.t('{name} from', { name })}
			value={writeTypedNumber(low)}
			onchange={(event) => (low = parseTypedNumber(event.currentTarget.value))}
		/>
		<span>{t.t('to')}</span>
		<input
			class="slider__number"
			inputmode="numeric"
			placeholder={t.t('no limit')}
			aria-label={t.t('{name} to', { name })}
			value={writeTypedNumber(high)}
			onchange={(event) => (high = parseTypedNumber(event.currentTarget.value))}
		/>
		<span class="slider__unit">{unit}</span>
	</div>
</div>
