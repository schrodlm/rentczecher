<!-- PROTOTYPE, throwaway. The wishes that order the shown listings, each
with an importance and its setting, a bar of how the score splits, and
three example listings scored live. -->
<script lang="ts">
	import LayoutChips from './LayoutChips.svelte';
	import PlacePicker from './PlacePicker.svelte';
	import RangeSlider from './RangeSlider.svelte';
	import {
		DISPOSITIONS, KINDS_COARSEST_FIRST, placeLabel,
		type Draft, type NamedPlace, type PlaceSearch
	} from './draft.svelte';
	import { examples, IMPORTANCE, ready, visibleWishes, weights, type Wish } from './scoring';
	import { kc, m2, priceStops, sizeStops, landStops } from './units';

	let { draft = $bindable(), search }: { draft: Draft; search: PlaceSearch } = $props();

	const TITLE: Record<Wish, string> = {
		price: 'A good price',
		pricePerM2: 'Value per m²',
		size: 'The right size',
		land: 'Enough land',
		layout: 'A layout you like',
		place: 'A spot you like'
	};
	const SHADE: Record<Wish, string> = {
		price: '#45462a', pricePerM2: '#6b6c45', size: '#8f9163', land: '#7e5920', layout: '#a87d3e', place: '#c9a26a'
	};

	const visible = $derived(visibleWishes(draft));
	const split = $derived(weights(draft));
	const active = $derived(visible.filter((w) => split[w] > 0));
	const cards = $derived(examples(draft));
	const layoutOptions = $derived(draft.layouts.length > 0 ? draft.layouts : DISPOSITIONS);

	function rule(wish: Wish): string {
		const good = draft.maxGoodPrice;
		if (wish === 'price') return good ? `Full points up to ${kc(good)}, none at ${kc(2 * good)} or more.` : 'Set your good price first.';
		if (wish === 'pricePerM2') return 'Full points at 300 Kč/m² or less, none at 550 Kč/m².';
		if (wish === 'size') return draft.idealSize ? `Full points at ${m2(draft.idealSize)} or more, half at ${m2(Math.round(draft.idealSize / 2))}.` : 'Set your ideal size first.';
		if (wish === 'land') return draft.idealLand ? `Full points at ${m2(draft.idealLand)} of land or more. Listings without land data get none.` : 'Set your ideal land first.';
		if (wish === 'layout') return draft.preferredDispositions.length ? 'Your 1st choice gets full points, each next one 20 fewer. Other layouts get 10.' : 'Pick the layouts you like, best first.';
		return draft.preferredPlaces.length ? 'Your 1st place gets full points, each next one 20 fewer. Elsewhere gets 20.' : 'Pick places inside your search, best first.';
	}

	function finerKinds(place: NamedPlace): string[] {
		return KINDS_COARSEST_FIRST.slice(KINDS_COARSEST_FIRST.indexOf(place.kind) + 1);
	}

	// Only places strictly finer than the search place and lying in it.
	async function searchInside(query: string): Promise<NamedPlace[]> {
		if (draft.place === null) return [];
		const found = await search(query, draft.place, finerKinds(draft.place));
		return found.filter((p) => !draft.preferredPlaces.some((q) => q.kind === p.kind && q.code === p.code));
	}

	function movePlace(index: number, by: number): void {
		const next = [...draft.preferredPlaces];
		const [item] = next.splice(index, 1);
		next.splice(index + by, 0, item);
		draft.preferredPlaces = next;
	}

	function tone(score: number): string {
		return score >= 70 ? 'good' : score >= 35 ? 'mid' : 'low';
	}
</script>

<div class="scoring">
	<div class="wishes">
		<p class="intro">Scoring only orders the listings you see, best first. It never hides any. Tell it what matters and how much.</p>

		{#if active.length > 0}
			<div class="split" aria-label="How the score splits">
				{#each active as wish (wish)}
					<span style:flex={split[wish]} style:background={SHADE[wish]} title="{TITLE[wish]} {split[wish]}%">{split[wish]}%</span>
				{/each}
			</div>
			<ul class="legend">
				{#each active as wish (wish)}<li><i style:background={SHADE[wish]}></i>{TITLE[wish]}</li>{/each}
			</ul>
		{/if}

		{#each visible as wish (wish)}
			<div class="wish" class:wish--on={split[wish] > 0}>
				<div class="wish__head">
					<strong>{TITLE[wish]}</strong>
					<div class="levels" role="radiogroup" aria-label="Importance">
						{#each IMPORTANCE as level, i (level)}
							<button
								type="button"
								class:on={draft.importance[wish] === i}
								disabled={i > 0 && !ready(draft, wish)}
								onclick={() => (draft.importance[wish] = i)}
							>{level}</button>
						{/each}
					</div>
				</div>

				{#if wish === 'price'}
					<RangeSlider single stops={priceStops(draft.offerType)} bind:value={draft.maxGoodPrice} unit="Kč" unset="good price" />
				{:else if wish === 'size'}
					<RangeSlider single stops={sizeStops} bind:value={draft.idealSize} unit="m²" unset="ideal size" />
				{:else if wish === 'land'}
					<RangeSlider single stops={landStops} bind:value={draft.idealLand} unit="m²" unset="ideal land" />
				{:else if wish === 'layout'}
					<LayoutChips ranked bind:selected={draft.preferredDispositions} options={layoutOptions} />
				{:else if wish === 'place'}
					{#if draft.place === null}
						<p class="rule">Choose where to search first.</p>
					{:else}
						<ol class="ranking">
							{#each draft.preferredPlaces as place, i (place.kind + place.code)}
								<li>
									<span class="rank">{['1st', '2nd', '3rd'][i] ?? `${i + 1}th`}</span>
									<span>{placeLabel(place)}</span>
									<button type="button" disabled={i === 0} onclick={() => movePlace(i, -1)}>↑</button>
									<button type="button" disabled={i === draft.preferredPlaces.length - 1} onclick={() => movePlace(i, 1)}>↓</button>
									<button type="button" onclick={() => draft.preferredPlaces.splice(i, 1)}>×</button>
								</li>
							{/each}
						</ol>
						<PlacePicker search={searchInside} placeholder="Add a part of your search area" onpick={(p) => draft.preferredPlaces.push(p)} />
					{/if}
				{/if}

				<p class="rule">{rule(wish)}</p>
			</div>
		{/each}
	</div>

	<aside class="examples">
		<h4>How listings would score</h4>
		{#if active.length === 0}
			<p class="empty">Every listing scores 0. Listings are shown newest first.</p>
		{:else}
			{#each cards as card (card.target)}
				<div class="example tone-{tone(card.total)}">
					<div class="example__top">
						<svg viewBox="0 0 40 40" class="glyph" aria-hidden="true">
							{#if draft.estateType === 'flat'}
								<rect x="9" y="6" width="22" height="30" rx="1" />
								{#each [10, 17, 24] as y (y)}<rect class="win" x="13" {y} width="5" height="4" /><rect class="win" x="22" {y} width="5" height="4" />{/each}
								<rect class="win" x="17" y="30" width="6" height="6" />
							{:else if draft.estateType === 'land'}
								<path d="M3 32 L14 20 L22 27 L29 18 L37 32 Z" /><line x1="3" y1="34" x2="37" y2="34" />
							{:else}
								<path d="M6 19 L20 7 L34 19 V35 H6 Z" /><rect class="win" x="12" y="22" width="6" height="6" /><rect class="win" x="22" y="24" width="6" height="11" />
							{/if}
						</svg>
						<div class="facts">
							{[card.listing.layout, card.listing.size ? m2(card.listing.size) : null, card.listing.land ? `${m2(card.listing.land)} land` : null].filter(Boolean).join(' · ')}
							<br /><b>{kc(card.listing.price)}</b> · {card.listing.place}
						</div>
						<div class="score">{card.total}</div>
					</div>
					{#if !card.exact}<p class="note">{card.target === 10 ? 'Lowest possible here' : card.target === 100 ? 'Highest possible here' : 'Closest to half'}: {card.total}</p>{/if}
					<ul class="parts">
						{#each card.parts as part (part.wish)}
							<li>
								<span class="part__fact">{part.fact}</span>
								<span class="part__bar"><i style:width="{part.max ? (100 * part.points) / part.max : 0}%"></i></span>
								<span class="part__pts">+{Math.round(part.points)} of {part.max}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		{/if}
	</aside>
</div>

<style>
	.scoring { display: grid; grid-template-columns: 1fr 20rem; gap: var(--space-6); align-items: start; }
	.intro { margin: 0 0 var(--space-3); color: var(--color-bronze); font-size: 0.875rem; }
	.split { display: flex; height: 1.5rem; border-radius: var(--radius-md); overflow: hidden; }
	.split span { display: flex; align-items: center; justify-content: center; color: #fff; font-size: 0.6875rem; font-weight: 700; min-width: 1.75rem; }
	.legend { display: flex; flex-wrap: wrap; gap: var(--space-1) var(--space-3); list-style: none; padding: 0; margin: var(--space-2) 0 var(--space-4); font-size: 0.75rem; }
	.legend i { display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 2px; margin-right: var(--space-1); }
	.wish { border: 1px solid var(--color-line); border-radius: var(--radius-md); padding: var(--space-3); margin-bottom: var(--space-3); background: var(--color-card); display: flex; flex-direction: column; gap: var(--space-2); }
	.wish--on { border-color: var(--color-olive); }
	.wish__head { display: flex; justify-content: space-between; align-items: center; gap: var(--space-3); }
	.levels { display: inline-flex; }
	.levels button { border: 1px solid var(--color-line); background: var(--color-ground); color: inherit; padding: var(--space-1) var(--space-2); font-size: 0.75rem; cursor: pointer; margin-left: -1px; }
	.levels button:first-child { border-radius: var(--radius-full) 0 0 var(--radius-full); }
	.levels button:last-child { border-radius: 0 var(--radius-full) var(--radius-full) 0; }
	.levels button.on { background: var(--color-olive); border-color: var(--color-olive); color: var(--color-ground); }
	.levels button:disabled { opacity: 0.35; cursor: not-allowed; }
	.rule { margin: 0; font-size: 0.8125rem; color: var(--color-bronze); }
	.ranking { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-1); }
	.ranking li { display: grid; grid-template-columns: 2.5rem 1fr auto auto auto; gap: var(--space-1); align-items: center; border: 1px solid var(--color-line); border-radius: var(--radius-md); padding: var(--space-1) var(--space-2); font-size: 0.875rem; }
	.rank { color: var(--color-bronze); font-size: 0.75rem; font-weight: 700; }
	.ranking button { background: none; border: none; color: var(--color-bronze); cursor: pointer; }
	.ranking button:disabled { opacity: 0.3; }
	.examples { position: sticky; top: 0; display: flex; flex-direction: column; gap: var(--space-3); }
	h4 { margin: 0; font-size: 0.875rem; }
	.empty { color: var(--color-bronze); font-size: 0.875rem; }
	.example { border: 1px solid var(--color-line); border-radius: var(--radius-md); padding: var(--space-3); background: var(--color-card); }
	.example__top { display: grid; grid-template-columns: 2.5rem 1fr auto; gap: var(--space-2); align-items: center; }
	.glyph { width: 2.5rem; height: 2.5rem; }
	.glyph rect, .glyph path { stroke: currentColor; stroke-width: 1.5; fill: color-mix(in srgb, currentColor 22%, transparent); }
	.glyph .win { fill: var(--color-card); stroke-width: 1; }
	.glyph line { stroke: currentColor; stroke-width: 1.5; }
	.facts { font-size: 0.75rem; line-height: 1.4; }
	.score { font-size: 1.75rem; font-weight: 800; font-variant-numeric: tabular-nums; }
	.tone-good { color: var(--color-olive); }
	.tone-mid { color: var(--color-bronze); }
	.tone-low { color: #a59f92; }
	.facts, .parts { color: var(--color-ink); }
	.note { margin: var(--space-1) 0 0; font-size: 0.6875rem; color: var(--color-bronze); }
	.parts { list-style: none; padding: 0; margin: var(--space-2) 0 0; display: flex; flex-direction: column; gap: 2px; }
	.parts li { display: grid; grid-template-columns: 1fr 3rem 4rem; gap: var(--space-2); align-items: center; font-size: 0.6875rem; }
	.part__bar { height: 4px; background: var(--color-line); border-radius: 2px; overflow: hidden; }
	.part__bar i { display: block; height: 100%; background: currentColor; }
	.parts li { color: inherit; }
	.part__fact { color: var(--color-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.part__pts { text-align: right; font-variant-numeric: tabular-nums; color: var(--color-ink); }
</style>
