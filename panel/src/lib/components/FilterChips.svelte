<script lang="ts">
	import { formatArea, formatPrice } from '$lib/format';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { layoutName } from '$lib/layouts';
	import { activeFacets, withoutFacet, type Facet, type ListingFilter } from '$lib/property-filter';
	import { shownPortal } from '$lib/portals';

	/* The filter's active parts as chips that each clear their part, and how
	many of the profile's listings it still shows. */
	let {
		filter = $bindable(),
		shown,
		count
	}: { filter: ListingFilter; shown: number; count: number } = $props();

	const t = getTranslatorContext();

	const facets = $derived(activeFacets(filter));

	function range(low: number | null, high: number | null, format: (value: number) => string): string {
		if (low !== null && high !== null) return `${format(low)} – ${format(high)}`;
		if (low !== null) return t.t('from {value}', { value: format(low) });
		return t.t('up to {value}', { value: format(high ?? 0) });
	}

	function label(facet: Facet): string {
		if (facet === 'portals') return filter.portals.map((portal) => shownPortal(portal)?.name ?? portal).join(', ');
		if (facet === 'priceDrops') return t.t('Only price drops');
		if (facet === 'score') return t.t('Score at least {score}', { score: filter.minimumScore ?? 0 });
		if (facet === 'layouts') return filter.layouts.map((layout) => layoutName(layout, t)).join(', ');
		if (facet === 'price') return range(filter.minPrice, filter.maxPrice, formatPrice);
		if (facet === 'size') return range(filter.minSize, filter.maxSize, formatArea);
		return `${t.t('Land')} ${range(filter.minLand, filter.maxLand, formatArea)}`;
	}
</script>

{#if facets.length > 0}
	<div class="filter-chips">
		{#each facets as facet (facet)}
			<button
				type="button"
				class="filter-chips__chip"
				aria-label={t.t('Clear {filter}', { filter: label(facet) })}
				onclick={() => (filter = withoutFacet(filter, facet))}
			>
				{label(facet)} <span aria-hidden="true">×</span>
			</button>
		{/each}
		<span class="filter-chips__count">{t.t('{shown} of {count} shown', { shown, count })}</span>
	</div>
{/if}

<style>
	.filter-chips {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--space-1) var(--space-2);
		padding: var(--space-2) var(--space-3) 0;
	}

	.filter-chips__chip {
		display: inline-flex;
		align-items: center;
		gap: var(--space-1);
		padding: 0.125rem var(--space-2);
		border: 1px solid color-mix(in srgb, var(--color-olive) 40%, var(--color-card));
		border-radius: var(--radius-full);
		background: color-mix(in srgb, var(--color-olive) 10%, var(--color-card));
		color: var(--color-ink);
		font-size: 0.75rem;
		cursor: pointer;
	}

	.filter-chips__chip:hover {
		border-color: var(--color-olive);
	}

	.filter-chips__count {
		margin-left: auto;
		color: var(--color-bronze);
		font-size: 0.75rem;
	}
</style>
