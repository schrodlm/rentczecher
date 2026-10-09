<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import type { components } from '$lib/api/types.gen';
	import LayoutChips from '$lib/forms/LayoutChips.svelte';
	import PreferredPlaces from '$lib/forms/PreferredPlaces.svelte';
	import ValueSlider from '$lib/forms/ValueSlider.svelte';
	import { LAND_SCALE, priceScale, SIZE_SCALE } from '$lib/forms/scale';
	import { formatArea, formatPrice } from '$lib/format';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { layoutName } from '$lib/layouts';
	import { kindsInside } from '$lib/places';
	import { exampleListings, type ExampleListing } from './examples';
	import PreferenceCard from './PreferenceCard.svelte';
	import type { ScorePart } from './score';
	import { switchOff, switchOn } from './split';
	import SplitBar from './SplitBar.svelte';
	import {
		countingFor,
		isReady,
		storedWeights,
		preferencesFor,
		type Weights,
		type Preference,
		type PreferredValues
	} from './preferences';

	type CriteriaBody = components['schemas']['CriteriaBody'];
	type PlaceRef = components['schemas']['PlaceRefModel'];

	/* The preferences that order a profile's listings: a split bar to weigh
	the counting ones against each other, a card per preference to switch it
	on and set what it scores against, and three example listings scored as
	they change. */
	let {
		criteria,
		searchPlace,
		preferredValues = $bindable(),
		weights = $bindable(),
		searchPlaces
	}: {
		criteria: Omit<CriteriaBody, 'place'>;
		searchPlace: NamedPlace | null;
		preferredValues: PreferredValues;
		weights: Weights;
		searchPlaces: (query: string, within: PlaceRef, kinds: PlaceRef['kind'][]) => Promise<NamedPlace[]>;
	} = $props();

	const t = getTranslatorContext();

	const preferences = $derived(preferencesFor(criteria.estate_type));
	const counting = $derived(countingFor(preferredValues, weights, criteria.estate_type));
	const shown = $derived(storedWeights(preferredValues, weights, criteria.estate_type));
	const examples = $derived(exampleListings({ criteria, searchPlace, preferredValues, weights }));

	function toggle(preference: Preference): void {
		weights = counting.includes(preference)
			? switchOff(shown, preference, counting)
			: switchOn(shown, preference, counting);
	}

	async function searchInside(query: string): Promise<NamedPlace[]> {
		if (searchPlace === null) return [];
		const kinds = kindsInside(searchPlace.kind);
		if (kinds.length === 0) return [];
		return searchPlaces(query, searchPlace, kinds);
	}

	function title(preference: Preference): string {
		if (preference === 'price') return t.t('Preferred price');
		if (preference === 'size') return t.t('Preferred size');
		if (preference === 'land') return t.t('Preferred land');
		if (preference === 'layout') return t.t('Preferred layouts');
		return t.t('Preferred places');
	}

	function shortName(preference: Preference): string {
		if (preference === 'price') return t.t('Price');
		if (preference === 'size') return t.t('Size');
		if (preference === 'land') return t.t('Land');
		if (preference === 'layout') return t.t('Layout');
		return t.t('Place');
	}

	function rule(preference: Preference): string {
		if (preference === 'price') {
			const preferred = preferredValues.preferred_price;
			if (preferred === null) return t.t('Set your preferred price first.');
			return t.t('Full points up to {preferred}, none at {twice} or more.', {
				preferred: formatPrice(preferred),
				twice: formatPrice(2 * preferred)
			});
		}
		if (preference === 'size') {
			const preferred = preferredValues.preferred_size_m2;
			if (preferred === null) return t.t('Set your preferred size first.');
			return t.t('Full points at {preferred} or more, half at {half}.', {
				preferred: formatArea(preferred),
				half: formatArea(Math.round(preferred / 2))
			});
		}
		if (preference === 'land') {
			const preferred = preferredValues.preferred_land_m2;
			if (preferred === null) return t.t('Set your preferred land first.');
			return t.t('Full points at {preferred} of land or more. Listings without land data get none.', {
				preferred: formatArea(preferred)
			});
		}
		if (preference === 'layout') {
			if (preferredValues.preferred_dispositions.length === 0) return t.t('Pick the layouts you like.');
			return t.t('Any of these layouts gets full points. Other layouts get 10.');
		}
		if (searchPlace === null) return t.t('Choose where to search first.');
		if (preferredValues.preferred_places.length === 0) return t.t('Pick places inside your search area.');
		return t.t('A listing in any of these places gets full points. Elsewhere gets 20.');
	}

	function layoutFact(card: ExampleListing): string {
		return card.layout === null ? '' : layoutName(card.layout, t);
	}

	function sizeFact(card: ExampleListing): string {
		return card.size === null ? '' : formatArea(card.size);
	}

	function landFact(card: ExampleListing): string {
		return card.land === null ? '' : t.t('{area} of land', { area: formatArea(card.land) });
	}

	function fact(card: ExampleListing, part: ScorePart): string {
		if (part.preference === 'price' || part.preference === 'pricePerM2') return formatPrice(card.price);
		if (part.preference === 'size') return sizeFact(card);
		if (part.preference === 'land') return landFact(card);
		if (part.preference === 'disposition') return layoutFact(card);
		return card.place?.name ?? '';
	}

	function facts(card: ExampleListing): string {
		return [layoutFact(card), sizeFact(card), landFact(card)].filter((part) => part !== '').join(' · ');
	}

	function missedTarget(card: ExampleListing): string {
		if (card.target === 100) return t.t('Highest possible here: {score}', { score: card.score });
		if (card.target === 10) return t.t('Lowest possible here: {score}', { score: card.score });
		return t.t('Closest to half: {score}', { score: card.score });
	}

	function partPreference(part: ScorePart): Preference {
		if (part.preference === 'pricePerM2') return 'price';
		if (part.preference === 'disposition') return 'layout';
		return part.preference;
	}

	function tone(score: number): string {
		if (score >= 70) return 'good';
		if (score >= 35) return 'mid';
		return 'low';
	}
</script>

<div class="scoring-section">
	<div class="scoring-section__preferences">
		<p class="scoring-section__hint">
			{t.t('Scoring only orders the listings you see, best first, and never hides any. Drag the dividers: the wider a preference, the more it decides.')}
		</p>

		{#if counting.length > 0}
			<SplitBar bind:weights={() => shown, (moved) => (weights = moved)} {counting} label={shortName} />
		{:else}
			<p class="scoring-section__empty">{t.t('Switch on a preference to start scoring.')}</p>
		{/if}

		<div class="scoring-section__cards">
			{#each preferences as preference (preference)}
				<PreferenceCard
					{preference}
					title={title(preference)}
					on={counting.includes(preference)}
					weight={shown[preference]}
					ready={isReady(preference, preferredValues)}
					rule={rule(preference)}
					ontoggle={() => toggle(preference)}
				>
					{#if preference === 'price'}
						<ValueSlider
							scale={priceScale(criteria.offer_type)}
							bind:value={preferredValues.preferred_price}
							name={t.t('Preferred price')}
							unit="Kč"
							placeholder={t.t('preferred price')}
						/>
					{:else if preference === 'size'}
						<ValueSlider
							scale={SIZE_SCALE}
							bind:value={preferredValues.preferred_size_m2}
							name={t.t('Preferred size')}
							unit="m²"
							placeholder={t.t('preferred size')}
						/>
					{:else if preference === 'land'}
						<ValueSlider
							scale={LAND_SCALE}
							bind:value={preferredValues.preferred_land_m2}
							name={t.t('Preferred land')}
							unit="m²"
							placeholder={t.t('preferred land')}
						/>
					{:else if preference === 'layout'}
						<LayoutChips bind:selected={preferredValues.preferred_dispositions} name={t.t('Preferred layouts')} />
					{:else}
						<PreferredPlaces
							bind:places={preferredValues.preferred_places}
							search={searchInside}
							placeholder={t.t('Add a part of your search area')}
						/>
					{/if}
				</PreferenceCard>
			{/each}
		</div>
	</div>

	<aside class="scoring-section__examples">
		<h4 class="scoring-section__heading">{t.t('How listings would score')}</h4>
		{#if counting.length === 0}
			<p class="scoring-section__hint">{t.t('Every listing scores 0 until a preference counts.')}</p>
		{:else}
			{#each examples as card (card.target)}
				<div class="example-card example-card--{tone(card.score)}">
					<div class="example-card__top">
						<svg viewBox="0 0 40 40" class="example-card__glyph" aria-hidden="true">
							{#if criteria.estate_type === 'flat'}
								<rect x="9" y="6" width="22" height="30" rx="1" />
								{#each [10, 17, 24] as y (y)}
									<rect class="example-card__window" x="13" {y} width="5" height="4" />
									<rect class="example-card__window" x="22" {y} width="5" height="4" />
								{/each}
								<rect class="example-card__window" x="17" y="30" width="6" height="6" />
							{:else if criteria.estate_type === 'land'}
								<path d="M3 32 L14 20 L22 27 L29 18 L37 32 Z" />
								<line x1="3" y1="34" x2="37" y2="34" />
							{:else}
								<path d="M6 19 L20 7 L34 19 V35 H6 Z" />
								<rect class="example-card__window" x="12" y="22" width="6" height="6" />
								<rect class="example-card__window" x="22" y="24" width="6" height="11" />
							{/if}
						</svg>
						<div class="example-card__facts">
							{facts(card)}
							<br /><b>{formatPrice(card.price)}</b>{#if card.place}&nbsp;· {card.place.name}{/if}
						</div>
						<div class="example-card__score">{card.score}</div>
					</div>
					{#if !card.nearTarget}
						<p class="example-card__note">{missedTarget(card)}</p>
					{/if}
					<ul class="example-card__parts">
						{#each card.parts as part (part.preference)}
							<li class="example-card__part preference-{partPreference(part)}">
								<span class="example-card__fact">{fact(card, part)}</span>
								<span class="example-card__bar">
									<i style:width="{(100 * part.points) / part.weight}%"></i>
								</span>
								<span class="example-card__points">
									{t.t('+{points} of {weight}', { points: Math.round(part.points), weight: part.weight })}
								</span>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		{/if}
	</aside>
</div>

<style>
	.scoring-section {
		display: grid;
		grid-template-columns: 1fr 20rem;
		gap: var(--space-6);
		align-items: start;
	}

	.scoring-section__preferences {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.scoring-section__hint {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.875rem;
	}

	/* As tall as the split bar it stands in for, so nothing moves when the
	first preference is switched on. */
	.scoring-section__empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 3.25rem;
		margin: 0;
		border: 1px dashed var(--color-line);
		border-radius: var(--radius-md);
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	.scoring-section__cards {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-3);
	}

	.scoring-section__examples {
		position: sticky;
		top: 0;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.scoring-section__heading {
		margin: 0;
		font-size: 0.875rem;
	}

	.example-card {
		padding: var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.example-card--good {
		color: var(--color-olive);
	}

	.example-card--mid {
		color: var(--color-amber);
	}

	.example-card--low {
		color: var(--color-bronze);
	}

	.example-card__top {
		display: grid;
		grid-template-columns: 2.5rem 1fr auto;
		gap: var(--space-2);
		align-items: center;
	}

	.example-card__glyph {
		width: 2.5rem;
		height: 2.5rem;
	}

	.example-card__glyph rect,
	.example-card__glyph path,
	.example-card__glyph line {
		stroke: currentColor;
		stroke-width: 1.5;
		fill: color-mix(in srgb, currentColor 22%, transparent);
	}

	.example-card__glyph .example-card__window {
		fill: var(--color-card);
		stroke-width: 1;
	}

	.example-card__facts {
		color: var(--color-ink);
		font-size: 0.75rem;
		line-height: 1.4;
	}

	.example-card__score {
		font-size: 1.75rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}

	.example-card__note {
		margin: var(--space-1) 0 0;
		color: var(--color-bronze);
		font-size: 0.6875rem;
	}

	.example-card__parts {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin: var(--space-2) 0 0;
		padding: 0;
		list-style: none;
	}

	.example-card__part {
		display: grid;
		grid-template-columns: 1fr 3rem 4rem;
		gap: var(--space-2);
		align-items: center;
		font-size: 0.6875rem;
	}

	.example-card__fact {
		overflow: hidden;
		color: var(--color-ink);
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.example-card__bar {
		height: 4px;
		overflow: hidden;
		border-radius: 2px;
		background: var(--color-line);
	}

	.example-card__bar i {
		display: block;
		height: 100%;
		background: var(--preference);
	}

	.example-card__points {
		color: var(--color-ink);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
</style>
