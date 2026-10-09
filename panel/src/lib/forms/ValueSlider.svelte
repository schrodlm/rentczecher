<script lang="ts">
	import '$lib/styles/slider.css';
	import { parseTypedNumber, writeTypedNumber, type Scale } from './scale';

	/* One value on a slider, typed beside it too. The handle at the start of
	the scale, or an empty box, is no value. A typed number is kept as typed,
	the handle goes to the nearest position. */
	let {
		scale,
		value = $bindable(),
		name,
		unit,
		placeholder
	}: {
		scale: Scale;
		value: number | null;
		name: string;
		unit: string;
		placeholder: string;
	} = $props();

	const index = $derived(value === null ? 0 : scale.nearestIndex(value));

	function slide(to: number): void {
		value = to === 0 ? null : scale.valueAt(to);
	}
</script>

<div class="slider">
	<div class="slider__track">
		<div class="slider__fill" style:left="0%" style:width="{(index / scale.lastIndex) * 100}%"></div>
		<input
			type="range"
			class="slider__handle"
			min="0"
			max={scale.lastIndex}
			value={index}
			aria-label={name}
			oninput={(event) => slide(Number(event.currentTarget.value))}
		/>
	</div>
	<div class="slider__numbers">
		<input
			class="slider__number"
			inputmode="numeric"
			{placeholder}
			aria-label={name}
			value={writeTypedNumber(value)}
			onchange={(event) => (value = parseTypedNumber(event.currentTarget.value))}
		/>
		<span class="slider__unit">{unit}</span>
	</div>
</div>
