<!-- PROTOTYPE, throwaway. Autocomplete over GET /v1/places. -->
<script lang="ts">
	import { placeLabel, type NamedPlace } from './draft.svelte';

	let {
		search,
		placeholder = 'Start typing a place...',
		disabled = false,
		onpick
	}: {
		search: (query: string) => Promise<NamedPlace[]>;
		placeholder?: string;
		disabled?: boolean;
		onpick: (place: NamedPlace) => void;
	} = $props();

	let query = $state('');
	let results = $state<NamedPlace[]>([]);
	let open = $state(false);

	async function update(): Promise<void> {
		const asked = query;
		if (asked.trim().length < 2) {
			results = [];
			return;
		}
		const found = await search(asked);
		if (asked === query) results = found;
	}

	function pick(place: NamedPlace): void {
		onpick(place);
		query = '';
		results = [];
		open = false;
	}
</script>

<div class="picker">
	<input
		type="search"
		bind:value={query}
		{placeholder}
		{disabled}
		oninput={() => {
			open = true;
			void update();
		}}
		onfocus={() => (open = true)}
		onblur={() => setTimeout(() => (open = false), 150)}
	/>
	{#if open && results.length > 0}
		<ul class="picker__results">
			{#each results as place (place.kind + place.code)}
				<li><button type="button" onmousedown={() => pick(place)}>{placeLabel(place)}</button></li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.picker {
		position: relative;
	}
	input {
		width: 100%;
		box-sizing: border-box;
	}
	.picker__results {
		position: absolute;
		z-index: 10;
		left: 0;
		right: 0;
		margin: 2px 0 0;
		padding: 0;
		list-style: none;
		background: var(--color-card);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		max-height: 16rem;
		overflow-y: auto;
		box-shadow: 0 4px 12px rgb(0 0 0 / 0.12);
	}
	.picker__results button {
		width: 100%;
		text-align: left;
		background: none;
		border: none;
		color: inherit;
		padding: var(--space-2) var(--space-3);
		cursor: pointer;
	}
	.picker__results button:hover {
		background: var(--color-ground);
	}
</style>
