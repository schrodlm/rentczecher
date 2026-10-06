<!-- PROTOTYPE, throwaway. Round 1, unmounted. Variant A: one long sectioned form, like a
settings page. Criteria lock into a summary once the profile exists. -->
<script lang="ts" module>
	export const name = 'Long form';
</script>

<script lang="ts">
	import PlacePicker from './PlacePicker.svelte';
	import {
		DISPOSITIONS, PORTALS, PORTAL_LABEL, placeLabel,
		type Draft, type PlaceSearch
	} from './draft.svelte';

	let {
		draft = $bindable(),
		editing,
		search,
		onsave,
		oncancel,
		ondelete
	}: {
		draft: Draft;
		editing: boolean;
		search: PlaceSearch;
		onsave: () => void;
		oncancel: () => void;
		ondelete: () => void;
	} = $props();

	function togglePortal(portal: (typeof PORTALS)[number]): void {
		draft.portals = draft.portals.includes(portal)
			? draft.portals.filter((p) => p !== portal)
			: [...draft.portals, portal];
	}

	function toggleDisposition(code: string): void {
		draft.preferredDispositions = draft.preferredDispositions.includes(code)
			? draft.preferredDispositions.filter((c) => c !== code)
			: [...draft.preferredDispositions, code];
	}
</script>

<div class="page">
	<header class="page__head">
		<h2>{editing ? 'Edit profile' : 'New profile'}</h2>
		{#if editing}
			<label class="pause"><input type="checkbox" bind:checked={draft.paused} /> Paused</label>
		{/if}
	</header>

	<section>
		<h3>Name</h3>
		<input class="wide" bind:value={draft.name} placeholder="Praha 7 byty" />
	</section>

	<section>
		<h3>Search</h3>
		{#if editing}
			<div class="locked">
				<p>
					{draft.offerType === 'rent' ? 'Rent' : 'Buy'} · {draft.estateType} ·
					{draft.place ? placeLabel(draft.place) : 'no place'}
					{#if draft.maxPrice}· up to {draft.maxPrice.toLocaleString('cs-CZ')} Kč{/if}
					{#if draft.minSize}· from {draft.minSize} m²{/if}
					{#if draft.minRooms || draft.maxRooms}· {draft.minRooms ?? 1} to {draft.maxRooms ?? 9} rooms{/if}
				</p>
				<small>The search is fixed once a profile exists. For a different search, create a new profile.</small>
			</div>
		{:else}
			<div class="grid">
				<label>Offer
					<select bind:value={draft.offerType}><option value="rent">Rent</option><option value="sale">Buy</option></select>
				</label>
				<label>Type
					<select bind:value={draft.estateType}>
						<option value="flat">Flat</option><option value="house">House</option>
						<option value="land">Land</option><option value="cottage">Cottage</option>
					</select>
				</label>
				<label class="span2">Place
					{#if draft.place}
						<span class="chip">{placeLabel(draft.place)} <button type="button" onclick={() => (draft.place = null)}>×</button></span>
					{:else}
						<PlacePicker {search} onpick={(p) => (draft.place = p)} />
					{/if}
				</label>
				<label>Price from (Kč)<input type="number" bind:value={draft.minPrice} /></label>
				<label>Price to (Kč)<input type="number" bind:value={draft.maxPrice} /></label>
				<label>Size from (m²)<input type="number" bind:value={draft.minSize} /></label>
				<label>Land from (m²)<input type="number" bind:value={draft.minLand} /></label>
				<label>Rooms from<input type="number" min="1" max="9" bind:value={draft.minRooms} /></label>
				<label>Rooms to<input type="number" min="1" max="9" bind:value={draft.maxRooms} /></label>
				<label>Kitchen
					<select bind:value={draft.kitchen}>
						<option value={null}>Any</option><option value="kitchenette">Kitchenette (+kk)</option>
						<option value="separate">Separate (+1)</option>
					</select>
				</label>
			</div>
		{/if}
	</section>

	<section>
		<h3>Portals</h3>
		{#each PORTALS as portal (portal)}
			<label class="inline"><input type="checkbox" checked={draft.portals.includes(portal)} onchange={() => togglePortal(portal)} /> {PORTAL_LABEL[portal]}</label>
		{/each}
	</section>

	<section>
		<h3>Scoring</h3>
		<p class="hint">Weights raise a listing's score and never hide it. Weights adding up to about 100 read as a percentage.</p>
		<table>
			<tbody>
				<tr><th>Price per m²</th><td><input type="number" min="0" bind:value={draft.pricePerM2Weight} /></td><td class="hint">cheaper per m² scores higher</td></tr>
				<tr><th>Price</th><td><input type="number" min="0" bind:value={draft.priceWeight} /></td><td>good price up to <input type="number" bind:value={draft.maxGoodPrice} /> Kč</td></tr>
				<tr><th>Size</th><td><input type="number" min="0" bind:value={draft.sizeWeight} /></td><td>ideal <input type="number" bind:value={draft.idealSize} /> m²</td></tr>
				<tr><th>Land</th><td><input type="number" min="0" bind:value={draft.landWeight} /></td><td>ideal <input type="number" bind:value={draft.idealLand} /> m²</td></tr>
				<tr><th>Layout</th><td><input type="number" min="0" bind:value={draft.dispositionWeight} /></td>
					<td class="codes">
						{#each DISPOSITIONS as code (code)}
							<button type="button" class="code" class:code--on={draft.preferredDispositions.includes(code)} onclick={() => toggleDisposition(code)}>
								{#if draft.preferredDispositions.includes(code)}<b>{draft.preferredDispositions.indexOf(code) + 1}.</b>{/if}{code}
							</button>
						{/each}
					</td>
				</tr>
				<tr><th>Place</th><td><input type="number" min="0" bind:value={draft.placeWeight} /></td>
					<td>
						<ol class="ranked">
							{#each draft.preferredPlaces as place, i (place.kind + place.code)}
								<li>{placeLabel(place)} <button type="button" onclick={() => draft.preferredPlaces.splice(i, 1)}>×</button></li>
							{/each}
						</ol>
						<PlacePicker {search} within={draft.place} placeholder="Add a preferred place inside the search place" onpick={(p) => draft.preferredPlaces.push(p)} />
					</td>
				</tr>
			</tbody>
		</table>
	</section>

	{#if editing}
		<section class="danger">
			<h3>Delete profile</h3>
			<p class="hint">The profile goes. Listings it found stay in the database.</p>
			<button type="button" class="btn-danger" onclick={ondelete}>Delete profile</button>
		</section>
	{/if}

	<footer class="bar">
		<button type="button" onclick={oncancel}>Cancel</button>
		<button type="button" class="btn-primary" onclick={onsave}>{editing ? 'Save' : 'Create profile'}</button>
	</footer>
</div>

<style>
	.page { max-width: 52rem; margin: 0 auto; padding: var(--space-4) var(--space-4) 5rem; }
	.page__head { display: flex; align-items: center; justify-content: space-between; }
	section { border-top: 1px solid var(--color-line); padding: var(--space-4) 0; }
	h3 { margin: 0 0 var(--space-3); font-size: 0.9375rem; color: var(--color-bronze); }
	.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-3); }
	.grid label { display: flex; flex-direction: column; gap: var(--space-1); font-size: 0.8125rem; }
	.span2 { grid-column: span 2; }
	.wide { width: 100%; box-sizing: border-box; }
	.inline { margin-right: var(--space-4); }
	.locked { background: var(--color-card); border: 1px dashed var(--color-line); border-radius: var(--radius-md); padding: var(--space-3); }
	.locked p { margin: 0 0 var(--space-1); }
	.hint, small { color: var(--color-bronze); font-size: 0.8125rem; }
	table { width: 100%; border-collapse: collapse; }
	th { text-align: left; width: 8rem; font-weight: 600; font-size: 0.875rem; }
	td, th { padding: var(--space-2) var(--space-2) var(--space-2) 0; vertical-align: top; }
	td input[type='number'] { width: 6rem; }
	.codes { display: flex; flex-wrap: wrap; gap: var(--space-1); }
	.code { border: 1px solid var(--color-line); background: var(--color-card); color: inherit; border-radius: var(--radius-full); padding: 0 var(--space-2); cursor: pointer; font-size: 0.8125rem; }
	.code--on { background: var(--color-olive); color: var(--color-ground); }
	.ranked { margin: 0 0 var(--space-2); padding-left: 1.25rem; }
	.chip { display: inline-flex; gap: var(--space-2); align-items: center; background: var(--color-card); border: 1px solid var(--color-line); border-radius: var(--radius-full); padding: var(--space-1) var(--space-3); }
	.chip button, .ranked button { background: none; border: none; color: var(--color-bronze); cursor: pointer; }
	.danger h3 { color: var(--color-ink); }
	.bar { position: fixed; bottom: 0; left: 11rem; right: 0; display: flex; justify-content: flex-end; gap: var(--space-2); padding: var(--space-3) var(--space-4); background: var(--color-card); border-top: 1px solid var(--color-line); }
	.btn-primary { background: var(--color-amber); color: var(--color-on-amber); border: none; border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); font-weight: 600; cursor: pointer; }
	.btn-danger { background: none; border: 1px solid var(--color-bronze); color: var(--color-bronze); border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); cursor: pointer; }
	.bar button:not(.btn-primary) { background: none; border: 1px solid var(--color-line); color: inherit; border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); cursor: pointer; }
	.pause { font-size: 0.875rem; }
</style>
