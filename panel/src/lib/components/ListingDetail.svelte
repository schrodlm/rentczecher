<script lang="ts">
	import type { ListingModel, PostingPricesModel } from '$lib/api/client';
	import { formatArea, formatPerM2, formatPrice, formatPricePerM2 } from '$lib/format';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { layoutName } from '$lib/layouts';
	import {
		factsOf,
		historyOf,
		isHighest,
		isLowest,
		layoutOf,
		percentAbove,
		percentBelow,
		percentFromMiddle,
		pricePerM2,
		standingOf,
		type ListingEvent,
		type Standing
	} from '$lib/listing-detail';
	import PlaceMap from '$lib/map/PlaceMap.svelte';
	import { shownPortal } from '$lib/portals';
	import { scoreListing, scoreParts, type ScorePart, type ScoringPreferences } from '$lib/scoring/score';
	import PriceChart from './PriceChart.svelte';
	import ScoreRing from './ScoreRing.svelte';
	import StandingStrip from './StandingStrip.svelte';

	/* The selected listing at length: its facts and links, why it scores what
	it does, how it compares within its profile, what happened to it and
	where it lies. A panel with nothing to say is left out. */
	let {
		listing,
		listings,
		preferences,
		priceHistory,
		onfavourite
	}: {
		listing: ListingModel;
		listings: readonly ListingModel[];
		preferences: ScoringPreferences | null;
		priceHistory: PostingPricesModel[] | null;
		onfavourite: (favourite: boolean) => void;
	} = $props();

	const t = getTranslatorContext();

	const portal = $derived(shownPortal(listing.source));
	const favourite = $derived(listing.favourited_at !== null);
	const score = $derived(preferences === null ? null : scoreListing(listing, preferences));
	const parts = $derived(preferences === null ? [] : scoreParts(listing, preferences));
	const history = $derived(historyOf(listing, priceHistory));
	const layout = $derived(layoutOf(listing, t));
	const facts = $derived(factsOf(listing, t));
	const priceStanding = $derived(standingOf(listing, listings, (each) => each.price));
	const sizeStanding = $derived(standingOf(listing, listings, (each) => each.size_m2));
	const perM2Standing = $derived(standingOf(listing, listings, pricePerM2));

	function priceSaying(standing: Standing): string {
		if (isLowest(standing)) return t.t('The cheapest in the profile');
		if (isHighest(standing)) return t.t('The dearest in the profile');
		return t.t("Cheaper than {percent} % of the profile's listings", { percent: percentAbove(standing) });
	}

	function sizeSaying(standing: Standing): string {
		if (isHighest(standing)) return t.t('The largest in the profile');
		if (isLowest(standing)) return t.t('The smallest in the profile');
		return t.t("Larger than {percent} % of the profile's listings", { percent: percentBelow(standing) });
	}

	function perM2Saying(standing: Standing): string {
		const fromMiddle = percentFromMiddle(standing);
		if (fromMiddle === 0) return t.t('Price per m² right in the middle of the profile');
		if (fromMiddle < 0) return t.t('Price per m² {percent} % below the middle of the profile', { percent: -fromMiddle });
		return t.t('Price per m² {percent} % above the middle of the profile', { percent: fromMiddle });
	}

	function partName(part: ScorePart): string {
		if (part.preference === 'price') return t.t('Price');
		if (part.preference === 'size') return t.t('Size');
		if (part.preference === 'land') return t.t('Land');
		if (part.preference === 'disposition') return t.t('Layout');
		if (part.preference === 'place') return t.t('Place');
		return t.t('Price per m²');
	}

	// The listing's own value beside the one the profile prefers.
	function partDetail(part: ScorePart): string {
		if (preferences === null) return '';
		if (part.preference === 'price' && listing.price !== null && preferences.preferred_price !== null) {
			return t.t('{value} · preferred up to {preferred}', {
				value: formatPrice(listing.price),
				preferred: formatPrice(preferences.preferred_price)
			});
		}
		if (part.preference === 'size' && listing.size_m2 !== null && preferences.preferred_size_m2 !== null) {
			return t.t('{value} · preferred {preferred}', {
				value: formatArea(listing.size_m2),
				preferred: formatArea(preferences.preferred_size_m2)
			});
		}
		if (part.preference === 'land' && listing.land_m2 !== null && preferences.preferred_land_m2 !== null) {
			return t.t('{value} · preferred {preferred}', {
				value: formatArea(listing.land_m2),
				preferred: formatArea(preferences.preferred_land_m2)
			});
		}
		if (part.preference === 'disposition' && layout !== null) {
			return t.t('{value} · preferred {preferred}', {
				value: layout,
				preferred: preferences.preferred_dispositions.map((each) => layoutName(each, t)).join(', ')
			});
		}
		if (part.preference === 'place') {
			return part.points > 0 ? t.t('In one of the preferred places') : t.t('Outside the preferred places');
		}
		return '';
	}

	function eventText(event: ListingEvent): string {
		if (event.kind === 'found') return t.t('First found');
		if (event.kind === 'viewed') return t.t('You viewed it');
		if (event.kind === 'favourite') return t.t('Added to favourites');
		if (event.to < event.from) {
			return t.t('Price dropped from {from} to {to}', { from: formatPrice(event.from), to: formatPrice(event.to) });
		}
		return t.t('Price rose from {from} to {to}', { from: formatPrice(event.from), to: formatPrice(event.to) });
	}

	function day(iso: string): string {
		return new Date(iso).toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric', year: 'numeric' });
	}
</script>

<article class="listing-detail">
	<header class="listing-detail__head">
		<span class="listing-detail__logo">
			{#if portal}<img src={portal.logo} alt="" />{/if}
		</span>
		<div class="listing-detail__headline">
			<div class="listing-detail__price">
				{listing.price === null ? '–' : formatPrice(listing.price)}
				{#if listing.price !== null && listing.size_m2 !== null}
					<small>{formatPricePerM2(listing.price, listing.size_m2)}</small>
				{/if}
			</div>
			<div class="listing-detail__facts">{facts}</div>
			<div class="listing-detail__actions">
				<button
					type="button"
					class="listing-detail__favourite"
					class:listing-detail__favourite--on={favourite}
					aria-pressed={favourite}
					onclick={() => onfavourite(!favourite)}
				>
					<span class="listing-detail__star" aria-hidden="true">{favourite ? '★' : '☆'}</span>
					{favourite ? t.t('In favourites') : t.t('Add to favourites')}
				</button>
				<a class="listing-detail__open" href={listing.url} target="_blank" rel="noopener noreferrer">
					{t.t('Open on {portal}', { portal: portal?.name ?? listing.source })} ↗
				</a>
				{#each listing.sibling_sources as sibling (sibling.source)}
					<a class="listing-detail__other" href={sibling.url} target="_blank" rel="noopener noreferrer">
						{t.t('also on {portal}', { portal: shownPortal(sibling.source)?.name ?? sibling.source })} ↗
					</a>
				{/each}
			</div>
		</div>
	</header>

	<div class="listing-detail__panels">
		{#if score !== null && parts.length > 0}
			<section class="listing-detail__panel listing-detail__score">
				<div class="listing-detail__ring"><ScoreRing {score} /></div>
			</section>

			<section class="listing-detail__panel">
				<h3>{t.tn('Why {count} point', 'Why {count} points', score)}</h3>
				<ul class="listing-detail__parts">
					{#each parts as part (part.preference)}
						<li>
							<div class="listing-detail__part-line">
								<b>{partName(part)}</b>
								<span>{t.t('+{points} of {weight}', { points: Math.round(part.points), weight: part.weight })}</span>
							</div>
							<span class="listing-detail__bar"><i style:width="{(100 * part.points) / part.weight}%"></i></span>
							<small>{partDetail(part)}</small>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if priceHistory}
			<section class="listing-detail__panel">
				<h3>{t.t('Price over time')}</h3>
				<PriceChart postings={priceHistory} />
			</section>
		{/if}

		{#if priceStanding || sizeStanding || perM2Standing}
			<section class="listing-detail__panel">
				<h3>{t.t('Compared within the profile')}</h3>
				<div class="listing-detail__standings">
					{#if priceStanding}
						<StandingStrip
							standing={priceStanding}
							label={t.t('Price')}
							format={formatPrice}
							saying={priceSaying(priceStanding)}
						/>
					{/if}
					{#if sizeStanding}
						<StandingStrip
							standing={sizeStanding}
							label={t.t('Size')}
							format={formatArea}
							saying={sizeSaying(sizeStanding)}
						/>
					{/if}
					{#if perM2Standing}
						<StandingStrip
							standing={perM2Standing}
							label={t.t('Price per m²')}
							format={formatPerM2}
							saying={perM2Saying(perM2Standing)}
						/>
					{/if}
				</div>
			</section>
		{/if}

		{#if listing.resolved_location !== null}
			<section class="listing-detail__panel">
				<h3>{t.t('Where')} · {listing.location_raw_text ?? listing.resolved_location.kraj.name}</h3>
				<div class="listing-detail__map"><PlaceMap location={listing.resolved_location} point={listing.point} /></div>
			</section>
		{/if}

		<section class="listing-detail__panel">
			<h3>{t.t('History')}</h3>
			<ol class="listing-detail__history">
				{#each history as event (`${event.kind}:${event.at}`)}
					<li><span>{day(event.at)}</span>{eventText(event)}</li>
				{/each}
			</ol>
		</section>
	</div>
</article>

<style>
	.listing-detail {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.listing-detail__head {
		display: grid;
		grid-template-columns: 4.5rem 1fr;
		align-items: start;
		gap: var(--space-4);
	}

	.listing-detail__logo {
		display: grid;
		place-items: center;
		width: 4.5rem;
		height: 4.5rem;
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.listing-detail__logo img {
		width: 3rem;
		height: 3rem;
		object-fit: contain;
	}

	.listing-detail__price {
		font-size: 1.75rem;
		font-weight: 800;
	}

	.listing-detail__price small {
		margin-left: var(--space-2);
		color: var(--color-bronze);
		font-size: 0.9375rem;
		font-weight: 400;
	}

	.listing-detail__facts {
		font-size: 1.0625rem;
	}

	.listing-detail__actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		margin-top: var(--space-3);
	}

	.listing-detail__favourite,
	.listing-detail__open,
	.listing-detail__other {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		color: var(--color-ink);
		font-size: 0.875rem;
		text-decoration: none;
		cursor: pointer;
	}

	.listing-detail__favourite--on {
		border-color: var(--color-gold);
	}

	.listing-detail__star {
		color: var(--color-gold);
		font-size: 1.125rem;
	}

	.listing-detail__open {
		border-color: var(--color-amber);
		background: var(--color-amber);
		color: var(--color-on-amber);
		font-weight: 700;
	}

	.listing-detail__score {
		display: grid;
		place-items: center;
	}

	.listing-detail__ring {
		width: 11rem;
	}

	.listing-detail__panels {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(19rem, 1fr));
		gap: var(--space-4);
	}

	.listing-detail__panel {
		padding: var(--space-4);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.listing-detail__panel h3 {
		margin: 0 0 var(--space-3);
		font-size: 0.9375rem;
	}

	.listing-detail__parts {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.listing-detail__part-line {
		display: flex;
		justify-content: space-between;
		font-size: 0.875rem;
	}

	.listing-detail__bar {
		display: block;
		height: 6px;
		margin: var(--space-1) 0;
		overflow: hidden;
		border-radius: 3px;
		background: var(--color-line);
	}

	.listing-detail__bar i {
		display: block;
		height: 100%;
		background: var(--color-olive);
	}

	.listing-detail__parts small {
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	.listing-detail__standings {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.listing-detail__map {
		height: 14rem;
	}

	.listing-detail__history {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: 0.875rem;
	}

	.listing-detail__history li {
		display: grid;
		grid-template-columns: 6.5rem 1fr;
		gap: var(--space-2);
	}

	.listing-detail__history span {
		color: var(--color-bronze);
		white-space: nowrap;
	}
</style>
