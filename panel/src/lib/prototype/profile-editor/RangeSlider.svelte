<!-- PROTOTYPE, throwaway. A slider over fixed stops with the numbers typed
beside it. With low and high bound it is a two-handle range, and the end
stops mean no bound. With only value bound it is a single handle. A typed
number is kept exactly, the handle goes to the nearest stop. -->
<script lang="ts">
	let {
		stops,
		low = $bindable(null),
		high = $bindable(null),
		value = $bindable(null),
		single = false,
		unit,
		openLow = 'any',
		openHigh = 'any',
		unset = 'not set'
	}: {
		stops: number[];
		low?: number | null;
		high?: number | null;
		value?: number | null;
		single?: boolean;
		unit: string;
		openLow?: string;
		openHigh?: string;
		unset?: string;
	} = $props();

	const last = $derived(stops.length - 1);

	function nearestIndex(n: number | null, fallback: number): number {
		if (n === null) return fallback;
		let best = 0;
		stops.forEach((s, i) => {
			if (Math.abs(s - n) < Math.abs(stops[best] - n)) best = i;
		});
		return best;
	}

	// The end stops mean no bound, and in single mode the first stop means
	// not set.
	const lowIndex = $derived(nearestIndex(low, 0));
	const highIndex = $derived(nearestIndex(high, last));
	const valueIndex = $derived(nearestIndex(value, 0));

	function setLow(i: number): void {
		const index = Math.min(i, highIndex);
		low = index === 0 ? null : stops[index];
	}

	function setHigh(i: number): void {
		const index = Math.max(i, lowIndex);
		high = index === last ? null : stops[index];
	}

	function typed(text: string): number | null {
		const digits = text.replace(/\s/g, '');
		return digits === '' || Number.isNaN(+digits) ? null : Math.max(0, Math.round(+digits));
	}
</script>

<div class="slider">
	<div class="track">
		{#if single}
			<div class="fill" style:left="0%" style:width="{(valueIndex / last) * 100}%"></div>
			<input type="range" min="0" max={last} value={valueIndex} oninput={(e) => (value = +e.currentTarget.value === 0 ? null : stops[+e.currentTarget.value])} />
		{:else}
			<div class="fill" style:left="{(lowIndex / last) * 100}%" style:width="{((highIndex - lowIndex) / last) * 100}%"></div>
			<input type="range" min="0" max={last} value={lowIndex} oninput={(e) => setLow(+e.currentTarget.value)} />
			<input type="range" min="0" max={last} value={highIndex} oninput={(e) => setHigh(+e.currentTarget.value)} />
		{/if}
	</div>
	<div class="numbers">
		{#if single}
			<input class="num" inputmode="numeric" placeholder={unset} value={value ?? ''} onchange={(e) => (value = typed(e.currentTarget.value))} />
		{:else}
			<input class="num" inputmode="numeric" placeholder={openLow} value={low ?? ''} onchange={(e) => (low = typed(e.currentTarget.value))} />
			<span>to</span>
			<input class="num" inputmode="numeric" placeholder={openHigh} value={high ?? ''} onchange={(e) => (high = typed(e.currentTarget.value))} />
		{/if}
		<span class="unit">{unit}</span>
	</div>
</div>

<style>
	.slider { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: var(--space-3); }
	.track { position: relative; height: 1.5rem; }
	.track::before { content: ''; position: absolute; left: 0; right: 0; top: 50%; height: 4px; margin-top: -2px; border-radius: 2px; background: var(--color-line); }
	.fill { position: absolute; top: 50%; height: 4px; margin-top: -2px; border-radius: 2px; background: var(--color-olive); }
	.track input { position: absolute; inset: 0; width: 100%; margin: 0; background: none; pointer-events: none; appearance: none; -webkit-appearance: none; }
	.track input::-webkit-slider-thumb { pointer-events: auto; -webkit-appearance: none; width: 1.1rem; height: 1.1rem; border-radius: 50%; background: var(--color-card); border: 2px solid var(--color-olive); cursor: grab; }
	.track input::-moz-range-thumb { pointer-events: auto; width: 1rem; height: 1rem; border-radius: 50%; background: var(--color-card); border: 2px solid var(--color-olive); cursor: grab; }
	.track input::-webkit-slider-runnable-track { background: none; }
	.track input::-moz-range-track { background: none; }
	.numbers { display: flex; align-items: center; gap: var(--space-1); font-size: 0.8125rem; color: var(--color-bronze); }
	.num { width: 6.5rem; padding: var(--space-1) var(--space-2); border: 1px solid var(--color-line); border-radius: var(--radius-md); background: var(--color-card); color: var(--color-ink); font-variant-numeric: tabular-nums; text-align: right; }
	.unit { min-width: 1.75rem; }
</style>
