<script lang="ts">
	import type { NamedPlace } from '$lib/api/client';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { placeLabel } from '$lib/places';

	let {
		search,
		placeholder,
		onpick
	}: {
		search: (query: string) => Promise<NamedPlace[]>;
		placeholder: string;
		onpick: (place: NamedPlace) => void;
	} = $props();

	const t = getTranslatorContext();
	// The engine answers only from two letters on.
	const MIN_QUERY_LENGTH = 2;

	const listId = $props.id();
	let query = $state('');
	let results = $state<NamedPlace[]>([]);
	let highlighted = $state(0);
	let open = $state(false);

	async function update(): Promise<void> {
		const asked = query.trim();
		if (asked.length < MIN_QUERY_LENGTH) {
			results = [];
			return;
		}
		const found = await search(asked);
		// An answer to a query the user has typed past is stale.
		if (asked !== query.trim()) return;
		results = found;
		highlighted = 0;
		open = true;
	}

	function pick(place: NamedPlace): void {
		onpick(place);
		query = '';
		results = [];
		open = false;
	}

	function onkeydown(event: KeyboardEvent): void {
		if (!open || results.length === 0) return;
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			highlighted = (highlighted + 1) % results.length;
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			highlighted = (highlighted - 1 + results.length) % results.length;
		} else if (event.key === 'Enter') {
			event.preventDefault();
			pick(results[highlighted]);
		} else if (event.key === 'Escape' && open) {
			// Only closes the list, so a dialog around the search stays open.
			event.preventDefault();
			open = false;
		}
	}
</script>

<div class="place-search">
	<input
		type="search"
		class="place-search__input"
		role="combobox"
		aria-expanded={open && results.length > 0}
		aria-controls={listId}
		aria-activedescendant={open && results.length > 0 ? `${listId}-${highlighted}` : undefined}
		aria-autocomplete="list"
		bind:value={query}
		{placeholder}
		oninput={() => void update()}
		onfocus={() => (open = true)}
		onblur={() => (open = false)}
		{onkeydown}
	/>
	{#if open && results.length > 0}
		<ul class="place-search__results" id={listId} role="listbox" aria-label={t.t('Places found')}>
			{#each results as place, index (`${place.kind}:${place.code}`)}
				<!-- Picked on mousedown, before the input's blur closes the list. -->
				<li
					id={`${listId}-${index}`}
					class="place-search__result"
					class:place-search__result--highlighted={index === highlighted}
					role="option"
					aria-selected={index === highlighted}
					onmousedown={(event) => {
						event.preventDefault();
						pick(place);
					}}
				>
					{placeLabel(place, t)}
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.place-search {
		position: relative;
	}

	.place-search__input {
		width: 100%;
		box-sizing: border-box;
		padding: var(--space-2) var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		color: inherit;
		font-size: 0.9375rem;
	}

	.place-search__results {
		position: absolute;
		z-index: 10;
		left: 0;
		right: 0;
		margin: var(--space-1) 0 0;
		padding: var(--space-1) 0;
		list-style: none;
		background: var(--color-card);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		max-height: 16rem;
		overflow-y: auto;
	}

	.place-search__result {
		padding: var(--space-2) var(--space-3);
		cursor: pointer;
	}

	.place-search__result--highlighted {
		background: var(--color-ground);
	}
</style>
