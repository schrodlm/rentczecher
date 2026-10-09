<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import { formatArea, formatPrice } from '$lib/format';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { layoutName } from '$lib/layouts';
	import { placeLabel } from '$lib/places';
	import type { Search } from './profile-draft.svelte';

	/* A stored profile's search, which is fixed, as one line of facts. */
	let { search, place }: { search: Search; place: NamedPlace } = $props();

	const t = getTranslatorContext();

	const facts = $derived(
		[
			what(),
			placeLabel(place, t),
			bounds(search.min_price, search.max_price, formatPrice),
			search.estate_type === 'land' ? null : bounds(search.min_size_m2, search.max_size_m2, formatArea),
			search.estate_type === 'flat' || search.min_land_m2 === null
				? null
				: t.t('land from {area}', { area: formatArea(search.min_land_m2) }),
			search.estate_type === 'land' || search.dispositions.length === 0
				? null
				: search.dispositions.map((layout) => layoutName(layout, t)).join(', ')
		].filter((fact) => fact !== null)
	);

	function what(): string {
		const rent = search.offer_type === 'rent';
		if (search.estate_type === 'flat') return rent ? t.t('Rent a flat') : t.t('Buy a flat');
		if (search.estate_type === 'house') return rent ? t.t('Rent a house') : t.t('Buy a house');
		if (search.estate_type === 'cottage') return rent ? t.t('Rent a cottage') : t.t('Buy a cottage');
		return rent ? t.t('Rent land') : t.t('Buy land');
	}

	function bounds(low: number | null, high: number | null, format: (value: number) => string): string | null {
		if (low !== null && high !== null) return t.t('{low} to {high}', { low: format(low), high: format(high) });
		if (low !== null) return t.t('from {low}', { low: format(low) });
		if (high !== null) return t.t('up to {high}', { high: format(high) });
		return null;
	}
</script>

<div class="search-summary">
	<p class="search-summary__facts">
		{#each facts as fact, index (index)}
			{#if index > 0}<span class="search-summary__dot" aria-hidden="true">·</span>{/if}
			<span class:search-summary__what={index === 0}>{fact}</span>
		{/each}
	</p>
	<p class="search-summary__note">
		{t.t('The search is fixed once a profile exists, because the listings it found answer it. For a different search, create a new profile.')}
	</p>
</div>

<style>
	.search-summary {
		padding: var(--space-3);
		border: 1px dashed var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.search-summary__facts {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1) var(--space-2);
		margin: 0 0 var(--space-2);
	}

	.search-summary__what {
		font-weight: 700;
	}

	.search-summary__dot {
		color: var(--color-bronze);
	}

	.search-summary__note {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}
</style>
