<script lang="ts">
	import PriceChart from '$lib/components/PriceChart.svelte';
	import PropertyRow from '$lib/components/PropertyRow.svelte';
	import ScoreRing from '$lib/components/ScoreRing.svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import MapCredit from '$lib/map/MapCredit.svelte';
	import PlaceMap from '$lib/map/PlaceMap.svelte';
	import { PORTALS } from '$lib/portals';
	import { ONE_FLAT, PRAHA_7, PRICE_HISTORY, RANKED_FLATS } from './sample-flats';

	/* What a profile does, in four slides built from the panel's own
	components showing made-up flats. */

	const t = getTranslatorContext();

	const SLIDES = 4;
	let slide = $state(0);
</script>

<div class="showcase">
	<div class="showcase__stage">
		{#if slide === 0}
			<div class="showcase__visual">
				<div class="showcase__map">
					<div class="showcase__map-shape"><PlaceMap location={PRAHA_7} point={null} /></div>
					<MapCredit />
				</div>
				<ul class="showcase__chips">
					<li>{t.t('Rent')}</li>
					<li>{t.t('Flat')}</li>
					<li>2+kk · 3+kk</li>
					<li>{t.t('up to {price}', { price: t.price(25000) })}</li>
					<li>{t.area(45)} – {t.area(80)}</li>
				</ul>
			</div>
			<h3>{t.t('Say what you are looking for')}</h3>
			<p>
				{t.t(
					'Pick the place on the map, from a whole region down to a street, then rent or buy, the price, the size and the layouts. A listing that misses any of them never shows.'
				)}
			</p>
		{:else if slide === 1}
			<div class="showcase__visual">
				<div class="showcase__portals">
					{#each PORTALS as portal (portal.portal)}
						<span class="showcase__portal"><img src={portal.logo} alt="" />{portal.name}</span>
					{/each}
				</div>
				<span class="showcase__arrow" aria-hidden="true">→</span>
				<div class="showcase__rows">
					<PropertyRow listing={ONE_FLAT} id="showcase-one" score={null} selected={false} onselect={() => {}} />
				</div>
			</div>
			<h3>{t.t('It watches the portals for you')}</h3>
			<p>
				{t.t(
					'Every scan searches the portals you picked. A flat posted on several of them shows once, with a link to each, and a new one is marked until you open it.'
				)}
			</p>
		{:else if slide === 2}
			<div class="showcase__visual">
				<div class="showcase__ring"><ScoreRing score={RANKED_FLATS[0].score} /></div>
				<div class="showcase__rows">
					{#each RANKED_FLATS as ranked (ranked.flat.id)}
						<PropertyRow
							listing={ranked.flat}
							id="showcase-{ranked.flat.id}"
							score={ranked.score}
							selected={ranked.flat === ONE_FLAT}
							onselect={() => {}}
						/>
					{/each}
				</div>
			</div>
			<h3>{t.t('The best flats come first')}</h3>
			<p>
				{t.t(
					'Tell the profile what you would prefer, a price, a size, a few places, and how much each matters. Every flat gets a score out of 100 that orders the list, and nothing is ever hidden for scoring low.'
				)}
			</p>
		{:else}
			<div class="showcase__visual">
				<div class="showcase__chart"><PriceChart postings={PRICE_HISTORY} ownListingId={ONE_FLAT.listing_id} /></div>
			</div>
			<h3>{t.t('Nothing slips past you')}</h3>
			<p>
				{t.t(
					'Each flat keeps its price history on every portal, so you see when it gets cheaper. Star the ones you like and they stay, even after the portals take them down.'
				)}
			</p>
		{/if}
	</div>

	<nav class="showcase__nav">
		<button class="showcase__step" disabled={slide === 0} aria-label={t.t('Previous')} onclick={() => (slide -= 1)}
			>‹</button
		>
		{#each { length: SLIDES }, index}
			<button
				class="showcase__dot"
				class:showcase__dot--on={index === slide}
				aria-label={t.t('Slide {n} of {count}', { n: index + 1, count: SLIDES })}
				onclick={() => (slide = index)}
			></button>
		{/each}
		<button
			class="showcase__step"
			disabled={slide === SLIDES - 1}
			aria-label={t.t('Next')}
			onclick={() => (slide += 1)}>›</button
		>
	</nav>
</div>

<style>
	.showcase {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.showcase__stage {
		min-height: 21rem;
	}

	.showcase__stage h3 {
		margin: var(--space-4) 0 var(--space-2);
		font-size: 1.0625rem;
	}

	.showcase__stage p {
		margin: 0;
		line-height: 1.5;
	}

	.showcase__visual {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-4);
		height: 14rem;
		padding: var(--space-3);
		box-sizing: border-box;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-ground);
	}

	.showcase__map {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: var(--space-1);
		width: 18rem;
		height: 100%;
	}

	.showcase__map-shape {
		flex: 1;
		min-height: 0;
		width: 100%;
	}

	.showcase__map-shape :global(svg) {
		width: 100%;
		height: 100%;
	}

	.showcase__chips {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		max-width: 14rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.showcase__chips li {
		padding: var(--space-1) var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		font-size: 0.8125rem;
	}

	.showcase__portals {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.showcase__portal {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-3) var(--space-1) var(--space-1);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		font-size: 0.8125rem;
	}

	.showcase__portal img {
		width: 1.25rem;
		height: 1.25rem;
	}

	.showcase__arrow {
		color: var(--color-amber);
		font-size: 1.5rem;
	}

	.showcase__rows {
		display: flex;
		flex-direction: column;
		width: 21rem;
		pointer-events: none;
	}

	.showcase__ring {
		width: 5.5rem;
	}

	.showcase__chart {
		width: 100%;
	}

	.showcase__nav {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
	}

	.showcase__dot {
		width: 0.5rem;
		height: 0.5rem;
		padding: 0;
		border: none;
		border-radius: var(--radius-full);
		background: var(--color-line);
		cursor: pointer;
	}

	.showcase__dot--on {
		background: var(--color-amber);
	}

	.showcase__step {
		border: none;
		background: none;
		color: var(--color-bronze);
		font-size: 1.25rem;
		cursor: pointer;
	}

	.showcase__step:disabled {
		opacity: 0.3;
		cursor: default;
	}
</style>
