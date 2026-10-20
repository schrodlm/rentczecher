<script lang="ts">
	import type { components } from '$lib/api/types.gen';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { kindName, NEARBY_KINDS } from './kinds';
	import type { NearbyStore } from './nearby-store.svelte';

	type PointModel = components['schemas']['PointModel'];

	/* What lies nearest the flat, one entry per kind its profile shows, and a
	block opening the list of every kind to choose from for the whole
	profile. */
	let { nearby, point }: { nearby: NearbyStore; point: PointModel | null } = $props();

	const t = getTranslatorContext();

	let choosing = $state(false);

	const chosen = $derived(NEARBY_KINDS.filter((each) => nearby.chosen.includes(each.kind)));
</script>

<div class="nearby-box">
	{#if point === null && chosen.length > 0}
		<p class="nearby-box__note">{t.t('Without an exact location, nothing can be measured.')}</p>
	{/if}
	{#if chosen.length > 0}
		<ul class="nearby-box__found">
			{#each chosen as shown (shown.kind)}
				{@const found = point === null ? null : nearby.nearestTo(point, shown.kind)}
				<li>
					<span class="nearby-box__kind">{kindName(shown.kind, t)}</span>
					<span class="nearby-box__distance">{found === null ? '–' : t.distance(found.distanceM)}</span>
					{#if found !== null}
						<span class="nearby-box__place">{found.place.name ?? t.t('unnamed')}</span>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
	<div class="nearby-box__adder">
		<button type="button" class="nearby-box__open" onclick={() => (choosing = true)}>
			<span class="nearby-box__plus" aria-hidden="true">+</span>
			{chosen.length === 0 ? t.t('Choose what to measure nearby') : t.t('Change what is measured nearby')}
		</button>
		{#if choosing}
			<div class="nearby-box__choice">
				<p class="nearby-box__note">{t.t('Shown for every flat in this profile.')}</p>
				<ul class="nearby-box__kinds">
					{#each NEARBY_KINDS as shown (shown.kind)}
						<li>
							<label>
								<input
									type="checkbox"
									checked={nearby.chosen.includes(shown.kind)}
									onchange={() => nearby.toggle(shown.kind)}
								/>
								{kindName(shown.kind, t)}
							</label>
						</li>
					{/each}
				</ul>
				<button type="button" class="nearby-box__done" onclick={() => (choosing = false)}>{t.t('Done')}</button>
			</div>
		{/if}
	</div>
	<p class="nearby-box__source">
		{t.t('Data from OpenStreetMap, asked for live. When its servers are busy, nothing shows for a while.')}
	</p>
</div>

<style>
	.nearby-box {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
	}

	.nearby-box__note {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.875rem;
	}

	.nearby-box__source {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.75rem;
	}

	.nearby-box__found {
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	/* The distance keeps its place on the first line, so a long place name
	gives way under it rather than pushing it out. */
	.nearby-box__found li {
		display: grid;
		grid-template-columns: 1fr auto;
		column-gap: var(--space-3);
	}

	.nearby-box__kind {
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}

	.nearby-box__distance {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.nearby-box__place {
		grid-column: 1 / -1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.nearby-box__open {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-2);
		width: 100%;
		padding: var(--space-3);
		border: 2px dashed var(--color-line);
		border-radius: var(--radius-md);
		background: none;
		color: var(--color-bronze);
		font: inherit;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.nearby-box__open:hover {
		border-color: var(--color-amber);
		color: var(--color-ink);
	}

	.nearby-box__plus {
		font-size: 1.25rem;
		font-weight: 700;
		line-height: 1;
	}

	.nearby-box__adder {
		position: relative;
	}

	/* The list floats over the block that opened it, so the panel keeps its
	size and the panels beside it do not grow with it. */
	.nearby-box__choice {
		position: absolute;
		top: 0;
		right: 0;
		left: 0;
		z-index: 20;
		display: flex;
		flex-direction: column;
		gap: var(--space-3);
		padding: var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
		box-shadow: 0 8px 24px rgb(0 0 0 / 18%);
	}

	.nearby-box__kinds {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
		gap: var(--space-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.nearby-box__kinds label {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		cursor: pointer;
	}

	.nearby-box__kinds input {
		accent-color: var(--color-amber);
	}

	.nearby-box__done {
		align-self: flex-end;
		padding: var(--space-1) var(--space-4);
		border: none;
		border-radius: var(--radius-md);
		background: var(--color-amber);
		color: var(--color-on-amber);
		font: inherit;
		font-weight: 600;
		cursor: pointer;
	}
</style>
