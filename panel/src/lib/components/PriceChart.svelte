<script lang="ts">
	import type { PostingPricesModel } from '$lib/api/client';
	import { formatPrice } from '$lib/format';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { shownPortal } from '$lib/portals';
	import { priceChartOf, type PlotBox } from '$lib/price-history';

	/* A listing's price over time as a step line for each portal posting of
	its flat, its own in amber, between the lowest and highest price any of
	them asked. An unchanged price is named once and says since when. */
	let { postings }: { postings: readonly PostingPricesModel[] } = $props();

	const t = getTranslatorContext();
	const BOX: PlotBox = { width: 320, height: 110, marginX: 6, marginY: 10 };

	const chart = $derived(priceChartOf(postings, BOX));
	const unchanged = $derived(chart !== null && chart.lowest === chart.highest);

	function portalName(source: string): string {
		return shownPortal(source)?.name ?? source;
	}

	function day(iso: string): string {
		return new Date(iso).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric' });
	}
</script>

{#if chart}
	<div class="price-chart">
		<div class="price-chart__plot">
			{#if unchanged}
				<span class="price-chart__price price-chart__price--level">{formatPrice(chart.highest)}</span>
			{:else}
				<span class="price-chart__price price-chart__price--high">{formatPrice(chart.highest)}</span>
				<span class="price-chart__price price-chart__price--low">{formatPrice(chart.lowest)}</span>
			{/if}
			<svg viewBox="0 0 {BOX.width} {BOX.height}" aria-hidden="true">
				{#if !unchanged}
					<line class="price-chart__guide" x1="0" x2={BOX.width} y1={BOX.marginY} y2={BOX.marginY} />
					<line
						class="price-chart__guide"
						x1="0"
						x2={BOX.width}
						y1={BOX.height - BOX.marginY}
						y2={BOX.height - BOX.marginY}
					/>
				{/if}
				{#each chart.lines as line (line.listingId)}
					<path class="price-chart__line" class:price-chart__line--own={line.own} d={line.path} />
					<circle class="price-chart__end" class:price-chart__end--own={line.own} cx={line.endX} cy={line.endY} r="3.5" />
				{/each}
			</svg>
		</div>
		<div class="price-chart__dates"><span>{day(chart.since)}</span><span>{day(chart.until)}</span></div>
		{#if unchanged}
			<p class="price-chart__saying">{t.t('The price has not changed since {date}', { date: day(chart.since) })}</p>
		{/if}
		{#if chart.lines.length > 1}
			<ul class="price-chart__legend">
				{#each chart.lines as line (line.listingId)}
					<li>
						<i class="price-chart__key" class:price-chart__key--own={line.own}></i>
						{portalName(line.source)} · {formatPrice(line.current)}
					</li>
				{/each}
			</ul>
		{/if}
	</div>
{/if}

<style>
	.price-chart {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.price-chart__plot {
		position: relative;
		padding-left: 5.5rem;
	}

	.price-chart__plot svg {
		display: block;
		width: 100%;
		height: auto;
		overflow: visible;
	}

	/* The labels sit at the guides' heights, which the plot's margin puts a
	tenth of the way in from each edge. */
	.price-chart__price {
		position: absolute;
		left: 0;
		color: var(--color-bronze);
		font-size: 0.75rem;
		font-variant-numeric: tabular-nums;
		transform: translateY(-50%);
	}

	.price-chart__price--high {
		top: 9%;
	}

	.price-chart__price--low {
		top: 91%;
	}

	.price-chart__price--level {
		top: 50%;
	}

	.price-chart__guide {
		stroke: var(--color-line);
		stroke-dasharray: 3 3;
	}

	.price-chart__line {
		fill: none;
		stroke: color-mix(in srgb, var(--color-bronze) 55%, var(--color-card));
		stroke-width: 2;
		stroke-linejoin: round;
	}

	.price-chart__line--own {
		stroke: var(--color-amber);
		stroke-width: 2.5;
	}

	.price-chart__end {
		fill: color-mix(in srgb, var(--color-bronze) 55%, var(--color-card));
	}

	.price-chart__end--own {
		fill: var(--color-amber);
	}

	.price-chart__dates {
		display: flex;
		justify-content: space-between;
		padding-left: 5.5rem;
		color: var(--color-bronze);
		font-size: 0.75rem;
	}

	.price-chart__saying {
		margin: 0;
		font-size: 0.8125rem;
	}

	.price-chart__legend {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-3);
		margin: 0;
		padding: 0;
		font-size: 0.8125rem;
		list-style: none;
	}

	.price-chart__key {
		display: inline-block;
		width: 0.75rem;
		height: 3px;
		margin-right: var(--space-1);
		vertical-align: middle;
		background: color-mix(in srgb, var(--color-bronze) 55%, var(--color-card));
	}

	.price-chart__key--own {
		background: var(--color-amber);
	}
</style>
