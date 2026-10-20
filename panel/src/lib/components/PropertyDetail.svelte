<script lang="ts">
	import type { GalleryModel, TrackedPropertyModel, PostingPricesModel } from '$lib/api/client';
	import { opensInBrowser } from '$lib/browser-link';
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
		type PropertyEvent,
		type Standing
	} from '$lib/property-detail';
	import MapCredit from '$lib/map/MapCredit.svelte';
	import PlaceMap from '$lib/map/PlaceMap.svelte';
	import { shownPortal } from '$lib/portals';
	import { scoreProperty, scoreParts, type ScorePart, type ScoringPreferences } from '$lib/scoring/score';
	import PhotoCollage from './PhotoCollage.svelte';
	import PriceChart from './PriceChart.svelte';
	import ScoreRing from './ScoreRing.svelte';
	import StandingStrip from './StandingStrip.svelte';

	/* The selected listing at length: its photos, its facts and links, why
	it scores what it does, how it compares within its profile, what happened
	to it and where it lies. A panel with nothing to say is left out. */
	let {
		listing,
		listings,
		preferences,
		priceHistory,
		gallery,
		onfavourite
	}: {
		listing: TrackedPropertyModel;
		listings: readonly TrackedPropertyModel[];
		preferences: ScoringPreferences | null;
		priceHistory: PostingPricesModel[] | null;
		gallery: GalleryModel | null;
		onfavourite: (favourite: boolean) => void;
	} = $props();

	const t = getTranslatorContext();

	const portal = $derived(shownPortal(listing.source));
	const favourite = $derived(listing.favourited_at !== null);
	const score = $derived(preferences === null ? null : scoreProperty(listing, preferences));
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
				value: t.price(listing.price),
				preferred: t.price(preferences.preferred_price)
			});
		}
		if (part.preference === 'size' && listing.size_m2 !== null && preferences.preferred_size_m2 !== null) {
			return t.t('{value} · preferred {preferred}', {
				value: t.area(listing.size_m2),
				preferred: t.area(preferences.preferred_size_m2)
			});
		}
		if (part.preference === 'land' && listing.land_m2 !== null && preferences.preferred_land_m2 !== null) {
			return t.t('{value} · preferred {preferred}', {
				value: t.area(listing.land_m2),
				preferred: t.area(preferences.preferred_land_m2)
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

	function eventText(event: PropertyEvent): string {
		if (event.kind === 'found') return t.t('First found');
		if (event.kind === 'viewed') return t.t('You viewed it');
		if (event.kind === 'favourite') return t.t('Added to favourites');
		if (event.to < event.from) {
			return t.t('Price dropped from {from} to {to}', { from: t.price(event.from), to: t.price(event.to) });
		}
		return t.t('Price rose from {from} to {to}', { from: t.price(event.from), to: t.price(event.to) });
	}

	function day(iso: string): string {
		return t.date(iso);
	}
</script>

<article class="property-detail">
	{#if gallery !== null}<PhotoCollage {gallery} />{/if}
	<header class="property-detail__head">
		<span class="property-detail__logo">
			{#if portal}<img src={portal.logo} alt="" />{/if}
		</span>
		<div class="property-detail__headline">
			<div class="property-detail__price">
				{listing.price === null ? '–' : t.price(listing.price)}
				{#if listing.price !== null && listing.size_m2 !== null}
					<small>{t.pricePerM2(listing.price, listing.size_m2)}</small>
				{/if}
			</div>
			<div class="property-detail__facts">{facts}</div>
			<div class="property-detail__actions">
				<button
					type="button"
					class="property-detail__favourite"
					class:property-detail__favourite--on={favourite}
					aria-pressed={favourite}
					onclick={() => onfavourite(!favourite)}
				>
					<span class="property-detail__star" aria-hidden="true">{favourite ? '★' : '☆'}</span>
					{favourite ? t.t('In favourites') : t.t('Add to favourites')}
				</button>
				<a
					class="property-detail__open"
					href={listing.url}
					target="_blank"
					rel="noopener noreferrer"
					use:opensInBrowser
				>
					{t.t('Open on {portal}', { portal: portal?.name ?? listing.source })} ↗
				</a>
				{#each listing.sibling_sources as sibling (sibling.source)}
					<a
						class="property-detail__other"
						href={sibling.url}
						target="_blank"
						rel="noopener noreferrer"
						use:opensInBrowser
					>
						{t.t('also on {portal}', { portal: shownPortal(sibling.source)?.name ?? sibling.source })} ↗
					</a>
				{/each}
			</div>
		</div>
	</header>

	<div class="property-detail__panels">
		{#if score !== null && parts.length > 0}
			<section class="property-detail__panel property-detail__score">
				<div class="property-detail__ring"><ScoreRing {score} /></div>
			</section>

			<section class="property-detail__panel">
				<h3>{t.tn('Why {count} point', 'Why {count} points', score)}</h3>
				<ul class="property-detail__parts">
					{#each parts as part (part.preference)}
						<li>
							<div class="property-detail__part-line">
								<b>{partName(part)}</b>
								<span>{t.t('+{points} of {weight}', { points: Math.round(part.points), weight: part.weight })}</span>
							</div>
							<span class="property-detail__bar"><i style:width="{(100 * part.points) / part.weight}%"></i></span>
							<small>{partDetail(part)}</small>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if priceHistory}
			<section class="property-detail__panel">
				<h3>{t.t('Price over time')}</h3>
				<PriceChart postings={priceHistory} ownListingId={listing.listing_id} />
			</section>
		{/if}

		{#if priceStanding || sizeStanding || perM2Standing}
			<section class="property-detail__panel">
				<h3>{t.t('Compared within the profile')}</h3>
				<div class="property-detail__standings">
					{#if priceStanding}
						<StandingStrip
							standing={priceStanding}
							label={t.t('Price')}
							format={(price) => t.price(price)}
							saying={priceSaying(priceStanding)}
						/>
					{/if}
					{#if sizeStanding}
						<StandingStrip
							standing={sizeStanding}
							label={t.t('Size')}
							format={(area) => t.area(area)}
							saying={sizeSaying(sizeStanding)}
						/>
					{/if}
					{#if perM2Standing}
						<StandingStrip
							standing={perM2Standing}
							label={t.t('Price per m²')}
							format={(perM2) => t.perM2(perM2)}
							saying={perM2Saying(perM2Standing)}
						/>
					{/if}
				</div>
			</section>
		{/if}

		{#if listing.resolved_location !== null}
			<section class="property-detail__panel">
				<h3>{t.t('Where')} · {listing.location_raw_text ?? listing.resolved_location.kraj.name}</h3>
				<div class="property-detail__map"><PlaceMap location={listing.resolved_location} point={listing.point} /></div>
				<div class="property-detail__map-credit"><MapCredit /></div>
			</section>
		{/if}

		<section class="property-detail__panel">
			<h3>{t.t('History')}</h3>
			<ol class="property-detail__history">
				{#each history as event (`${event.kind}:${event.at}`)}
					<li><span>{day(event.at)}</span>{eventText(event)}</li>
				{/each}
			</ol>
		</section>
	</div>
</article>

<style>
	.property-detail {
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
	}

	.property-detail__head {
		display: grid;
		grid-template-columns: 4.5rem 1fr;
		align-items: start;
		gap: var(--space-4);
	}

	.property-detail__logo {
		display: grid;
		place-items: center;
		width: 4.5rem;
		height: 4.5rem;
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.property-detail__logo img {
		width: 3rem;
		height: 3rem;
		object-fit: contain;
	}

	.property-detail__price {
		font-size: 1.75rem;
		font-weight: 800;
	}

	.property-detail__price small {
		margin-left: var(--space-2);
		color: var(--color-bronze);
		font-size: 0.9375rem;
		font-weight: 400;
	}

	.property-detail__facts {
		font-size: 1.0625rem;
	}

	.property-detail__actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		margin-top: var(--space-3);
	}

	.property-detail__favourite,
	.property-detail__open,
	.property-detail__other {
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

	.property-detail__favourite--on {
		border-color: var(--color-gold);
	}

	.property-detail__star {
		color: var(--color-gold);
		font-size: 1.125rem;
	}

	.property-detail__open {
		border-color: var(--color-amber);
		background: var(--color-amber);
		color: var(--color-on-amber);
		font-weight: 700;
	}

	.property-detail__score {
		display: grid;
		place-items: center;
	}

	.property-detail__ring {
		width: 11rem;
	}

	.property-detail__panels {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(19rem, 1fr));
		gap: var(--space-4);
	}

	.property-detail__panel {
		padding: var(--space-4);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.property-detail__panel h3 {
		margin: 0 0 var(--space-3);
		font-size: 0.9375rem;
	}

	.property-detail__parts {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.property-detail__part-line {
		display: flex;
		justify-content: space-between;
		font-size: 0.875rem;
	}

	.property-detail__bar {
		display: block;
		height: 6px;
		margin: var(--space-1) 0;
		overflow: hidden;
		border-radius: 3px;
		background: var(--color-line);
	}

	.property-detail__bar i {
		display: block;
		height: 100%;
		background: var(--color-olive);
	}

	.property-detail__parts small {
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	.property-detail__standings {
		display: flex;
		flex-direction: column;
		gap: var(--space-4);
	}

	.property-detail__map {
		height: 14rem;
	}

	.property-detail__map-credit {
		margin-top: var(--space-1);
		text-align: right;
	}

	.property-detail__history {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: 0.875rem;
	}

	.property-detail__history li {
		display: grid;
		grid-template-columns: 6.5rem 1fr;
		gap: var(--space-2);
	}

	.property-detail__history span {
		color: var(--color-bronze);
		white-space: nowrap;
	}
</style>
