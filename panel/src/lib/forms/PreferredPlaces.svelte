<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import PlaceSearch from '$lib/components/PlaceSearch.svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { placeLabel } from '$lib/places';

	/* The places a profile prefers, picked by name and each removable. A place
	already picked is not offered again. */
	let {
		places = $bindable(),
		search,
		placeholder
	}: { places: NamedPlace[]; search: (query: string) => Promise<NamedPlace[]>; placeholder: string } = $props();

	const t = getTranslatorContext();

	function isPicked(place: NamedPlace): boolean {
		return places.some((picked) => picked.kind === place.kind && picked.code === place.code);
	}

	async function searchUnpicked(query: string): Promise<NamedPlace[]> {
		const found = await search(query);
		return found.filter((place) => !isPicked(place));
	}

	function remove(place: NamedPlace): void {
		places = places.filter((picked) => picked !== place);
	}
</script>

<div class="preferred-places">
	<PlaceSearch search={searchUnpicked} {placeholder} onpick={(place) => (places = [...places, place])} />
	{#if places.length > 0}
		<ul class="preferred-places__picked">
			{#each places as place (`${place.kind}:${place.code}`)}
				<li class="preferred-places__chip">
					{placeLabel(place, t)}
					<button
						type="button"
						class="preferred-places__remove"
						aria-label={t.t('Remove {name}', { name: placeLabel(place, t) })}
						onclick={() => remove(place)}>×</button
					>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.preferred-places {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
	}

	.preferred-places__picked {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.preferred-places__chip {
		display: inline-flex;
		align-items: center;
		padding: 0 var(--space-1) 0 var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		font-size: 0.875rem;
	}

	.preferred-places__remove {
		padding: var(--space-1);
		border: none;
		background: none;
		color: var(--color-bronze);
		font-size: 1rem;
		line-height: 1;
		cursor: pointer;
	}
</style>
