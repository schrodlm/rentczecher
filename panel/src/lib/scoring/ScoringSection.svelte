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
	import type { ScorePart } from './score';
	import WishCard from './WishCard.svelte';
	import {
		isReady,
		preferencesFor,
		weightsOf,
		wishesFor,
		type Importance,
		type Importances,
		type Wish,
		type WishSettings
	} from './wishes';

	type CriteriaBody = components['schemas']['CriteriaBody'];
	type PlaceRef = components['schemas']['PlaceRefModel'];

	/* The wishes that order a profile's listings, each with its importance and
	setting, how the score splits between them, and three example listings
	scored as the wishes change. */
	let {
		criteria,
		searchPlace,
		settings = $bindable(),
		importances = $bindable(),
		searchPlaces
	}: {
		criteria: Omit<CriteriaBody, 'place'>;
		searchPlace: NamedPlace | null;
		settings: WishSettings;
		importances: Importances;
		searchPlaces: (query: string, within: PlaceRef, kinds: PlaceRef['kind'][]) => Promise<NamedPlace[]>;
	} = $props();

	const t = getTranslatorContext();

	const wishes = $derived(wishesFor(criteria.estate_type));
	const preferences = $derived(preferencesFor(settings, importances, criteria.estate_type));
	const weights = $derived(weightsOf(settings, importances, criteria.estate_type));
	const counting = $derived(wishes.filter((wish) => weights[wish] > 0));
	const examples = $derived(
		exampleListings({ criteria, searchPlace, preferences, preferredPlaces: settings.preferred_places })
	);

	// A wish without its setting shows as off whatever importance it was given.
	function importanceOf(wish: Wish): Importance {
		return isReady(wish, settings) ? importances[wish] : 0;
	}

	function setImportance(wish: Wish, level: Importance): void {
		importances = { ...importances, [wish]: level };
	}

	async function searchInside(query: string): Promise<NamedPlace[]> {
		if (searchPlace === null) return [];
		const kinds = kindsInside(searchPlace.kind);
		if (kinds.length === 0) return [];
		return searchPlaces(query, searchPlace, kinds);
	}

	function title(wish: Wish): string {
		if (wish === 'price') return t.t('A good price');
		if (wish === 'size') return t.t('The right size');
		if (wish === 'land') return t.t('Enough land');
		if (wish === 'layout') return t.t('A layout you like');
		return t.t('A spot you like');
	}

	function rule(wish: Wish): string {
		if (wish === 'price') {
			const good = settings.max_good_price;
			if (good === null) return t.t('Set your good price first.');
			return t.t('Full points up to {good}, none at {twice} or more.', {
				good: formatPrice(good),
				twice: formatPrice(2 * good)
			});
		}
		if (wish === 'size') {
			const ideal = settings.ideal_size_m2;
			if (ideal === null) return t.t('Set your ideal size first.');
			return t.t('Full points at {ideal} or more, half at {half}.', {
				ideal: formatArea(ideal),
				half: formatArea(Math.round(ideal / 2))
			});
		}
		if (wish === 'land') {
			const ideal = settings.ideal_land_m2;
			if (ideal === null) return t.t('Set your ideal land first.');
			return t.t('Full points at {ideal} of land or more. Listings without land data get none.', {
				ideal: formatArea(ideal)
			});
		}
		if (wish === 'layout') {
			if (settings.preferred_dispositions.length === 0) return t.t('Pick the layouts you like.');
			return t.t('Any of these layouts gets full points. Other layouts get 10.');
		}
		if (searchPlace === null) return t.t('Choose where to search first.');
		if (settings.preferred_places.length === 0) return t.t('Pick places inside your search area.');
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

	function tone(score: number): string {
		if (score >= 70) return 'good';
		if (score >= 35) return 'mid';
		return 'low';
	}
</script>

<div class="scoring-section">
	<div class="scoring-section__wishes">
		<p class="scoring-section__hint">
			{t.t('Scoring only orders the listings you see, best first. It never hides any. Tell it what matters and how much.')}
		</p>

		{#if counting.length > 0}
			<div class="scoring-section__split" aria-label={t.t('How the score splits')}>
				{#each counting as wish (wish)}
					<span class="scoring-section__share scoring-section__share--{wish}" style:flex-grow={weights[wish]}></span>
				{/each}
			</div>
			<ul class="scoring-section__legend">
				{#each counting as wish (wish)}
					<li>
						<i class="scoring-section__swatch scoring-section__share--{wish}"></i>{title(wish)}
						{weights[wish]} %
					</li>
				{/each}
			</ul>
		{/if}

		{#each wishes as wish (wish)}
			<WishCard
				title={title(wish)}
				bind:importance={() => importanceOf(wish), (level) => setImportance(wish, level)}
				ready={isReady(wish, settings)}
				rule={rule(wish)}
			>
				{#if wish === 'price'}
					<ValueSlider
						scale={priceScale(criteria.offer_type)}
						bind:value={settings.max_good_price}
						name={t.t('Good price')}
						unit="Kč"
						placeholder={t.t('good price')}
					/>
				{:else if wish === 'size'}
					<ValueSlider
						scale={SIZE_SCALE}
						bind:value={settings.ideal_size_m2}
						name={t.t('Ideal size')}
						unit="m²"
						placeholder={t.t('ideal size')}
					/>
				{:else if wish === 'land'}
					<ValueSlider
						scale={LAND_SCALE}
						bind:value={settings.ideal_land_m2}
						name={t.t('Ideal land')}
						unit="m²"
						placeholder={t.t('ideal land')}
					/>
				{:else if wish === 'layout'}
					<LayoutChips bind:selected={settings.preferred_dispositions} name={t.t('Layouts you like')} />
				{:else}
					<PreferredPlaces
						bind:places={settings.preferred_places}
						search={searchInside}
						placeholder={t.t('Add a part of your search area')}
					/>
				{/if}
			</WishCard>
		{/each}
	</div>

	<aside class="scoring-section__examples">
		<h4 class="scoring-section__heading">{t.t('How listings would score')}</h4>
		{#if counting.length === 0}
			<p class="scoring-section__hint">{t.t('Every listing scores 0 until a wish counts.')}</p>
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
							<li class="example-card__part">
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

	.scoring-section__wishes {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.scoring-section__hint {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.875rem;
	}

	.scoring-section__split {
		display: flex;
		gap: 2px;
		height: 0.75rem;
		border-radius: var(--radius-md);
		overflow: hidden;
	}

	.scoring-section__share--price {
		background: var(--color-olive);
	}

	.scoring-section__share--size {
		background: var(--color-amber);
	}

	.scoring-section__share--land {
		background: var(--color-bronze);
	}

	.scoring-section__share--layout {
		background: color-mix(in srgb, var(--color-olive) 50%, var(--color-card));
	}

	.scoring-section__share--place {
		background: color-mix(in srgb, var(--color-amber) 50%, var(--color-card));
	}

	.scoring-section__legend {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-3);
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: 0.75rem;
	}

	.scoring-section__swatch {
		display: inline-block;
		width: 0.6rem;
		height: 0.6rem;
		margin-right: var(--space-1);
		border-radius: 2px;
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
		background: currentColor;
	}

	.example-card__points {
		color: var(--color-ink);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
</style>
