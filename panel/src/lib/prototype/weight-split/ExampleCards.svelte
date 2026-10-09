<!-- PROTOTYPE, throwaway. Example listings scored live from the weights. -->
<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import { formatArea, formatPrice } from '$lib/format';
	import { exampleListings } from '$lib/scoring/examples';
	import type { SplitState } from './split.svelte';

	let { split }: { split: SplitState } = $props();

	const PRAHA: NamedPlace = { kind: 'obec', code: 554782, name: 'Praha', obec: null, okres: null };
	const CRITERIA = {
		estate_type: 'flat',
		offer_type: 'rent',
		min_price: null,
		max_price: null,
		min_size_m2: null,
		max_size_m2: null,
		min_land_m2: null,
		dispositions: []
	} as const;

	const cards = $derived(
		exampleListings({
			criteria: { ...CRITERIA, dispositions: [] },
			searchPlace: PRAHA,
			preferences: {
				price_per_m2_weight: 0,
				disposition_weight: split.weights.layout,
				preferred_dispositions: split.settings.preferred_dispositions,
				size_weight: split.weights.size,
				ideal_size_m2: split.settings.ideal_size_m2,
				place_weight: split.weights.place,
				land_weight: split.weights.land,
				ideal_land_m2: split.settings.ideal_land_m2,
				price_weight: split.weights.price,
				max_good_price: split.settings.max_good_price
			},
			preferredPlaces: split.settings.preferred_places
		})
	);

	const NAMES: Record<string, string> = {
		price: 'Cena',
		size: 'Velikost',
		land: 'Pozemek',
		disposition: 'Dispozice',
		place: 'Místo',
		pricePerM2: 'Cena za m²'
	};
	const CLASS: Record<string, string> = {
		price: 'pref-price',
		size: 'pref-size',
		land: 'pref-land',
		disposition: 'pref-layout',
		place: 'pref-place',
		pricePerM2: 'pref-price'
	};
</script>

<aside class="examples">
	<h4 class="examples__heading">Jak by inzeráty bodovaly</h4>
	{#each cards as card (card.target)}
		<div class="examples__card">
			<div class="examples__top">
				<div class="examples__facts">
					{[card.layout, card.size ? formatArea(card.size) : null].filter(Boolean).join(' · ')}
					<br /><b>{formatPrice(card.price)}</b> · {card.place?.name ?? ''}
				</div>
				<div class="examples__score">{card.score}</div>
			</div>
			<div class="examples__stack">
				{#each card.parts as part (part.preference)}
					<i class={CLASS[part.preference]} style:flex-grow={part.points} title="{NAMES[part.preference]} +{Math.round(part.points)}"></i>
				{/each}
				<i class="examples__missing" style:flex-grow={100 - card.score}></i>
			</div>
		</div>
	{/each}
</aside>

<style>
	.examples {
		position: sticky;
		top: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.examples__heading {
		margin: 0;
		font-size: 0.875rem;
	}

	.examples__card {
		padding: var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.examples__top {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.examples__facts {
		font-size: 0.75rem;
		line-height: 1.4;
	}

	.examples__score {
		font-size: 1.75rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}

	.examples__stack {
		display: flex;
		gap: 2px;
		height: 6px;
		margin-top: var(--space-2);
		border-radius: 3px;
		overflow: hidden;
	}

	.examples__stack i {
		background: var(--pref);
	}

	.examples__stack .examples__missing {
		background: var(--color-line);
	}
</style>
