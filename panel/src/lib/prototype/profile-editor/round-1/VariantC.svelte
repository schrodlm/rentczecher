<!-- PROTOTYPE, throwaway. Round 1, unmounted. Variant C: a drawer over the inbox, compact
collapsible sections, sliders for the weights with a live bar of how the
score splits, and a preview of the tab and its search. -->
<script lang="ts" module>
	export const name = 'Drawer with live split';
	export const overlay = true;
</script>

<script lang="ts">
	import PlacePicker from './PlacePicker.svelte';
	import {
		DISPOSITIONS, PORTALS, PORTAL_LABEL, placeLabel, weights,
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

	// svelte-ignore state_referenced_locally
	let openSection = $state<'search' | 'portals' | 'scoring'>(editing ? 'scoring' : 'search');
	let menuOpen = $state(false);

	const SHADES = ['var(--color-olive)', 'var(--color-bronze)', 'var(--color-amber)', '#8a8b5a', '#b08850', '#e9b56b'];
	const split = $derived(weights(draft));
	const total = $derived(split.reduce((sum, part) => sum + part.weight, 0));

	const searchChips = $derived(
		[
			draft.offerType === 'rent' ? 'Rent' : 'Buy',
			draft.estateType,
			draft.place?.name ?? 'no place yet',
			draft.maxPrice ? `≤ ${draft.maxPrice.toLocaleString('cs-CZ')} Kč` : null,
			draft.minSize ? `≥ ${draft.minSize} m²` : null,
			draft.minRooms || draft.maxRooms ? `${draft.minRooms ?? 1}–${draft.maxRooms ?? 9} rooms` : null
		].filter(Boolean)
	);

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

<div class="scrim" role="presentation" onclick={oncancel}></div>
<aside class="drawer">
	<header class="drawer__head">
		<input class="title" bind:value={draft.name} placeholder="Name this profile" />
		{#if editing}
			<label class="switch" title="Paused profiles are skipped by scans">
				<input type="checkbox" checked={!draft.paused} onchange={() => (draft.paused = !draft.paused)} />
				{draft.paused ? 'Paused' : 'Watching'}
			</label>
			<div class="menu">
				<button type="button" onclick={() => (menuOpen = !menuOpen)}>⋯</button>
				{#if menuOpen}
					<div class="menu__pop"><button type="button" onclick={ondelete}>Delete profile</button></div>
				{/if}
			</div>
		{/if}
	</header>

	<div class="preview">
		<span class="preview__tab">{draft.name || 'New profile'}</span>
		{#each searchChips as chip (chip)}<span class="preview__chip">{chip}</span>{/each}
	</div>

	<section class:open={openSection === 'search'}>
		<button type="button" class="section__head" onclick={() => (openSection = 'search')}>
			Search {#if editing}<span class="lock">fixed</span>{/if}
		</button>
		{#if openSection === 'search'}
			{#if editing}
				<p class="hint">The search is fixed once a profile exists. Duplicate this profile to search differently.</p>
				<button type="button" class="ghost">Duplicate as a new profile</button>
			{:else}
				<div class="seg">
					<button type="button" class:on={draft.offerType === 'rent'} onclick={() => (draft.offerType = 'rent')}>Rent</button>
					<button type="button" class:on={draft.offerType === 'sale'} onclick={() => (draft.offerType = 'sale')}>Buy</button>
				</div>
				<div class="seg">
					{#each ['flat', 'house', 'land', 'cottage'] as const as type (type)}
						<button type="button" class:on={draft.estateType === type} onclick={() => (draft.estateType = type)}>{type}</button>
					{/each}
				</div>
				{#if draft.place}
					<div class="chip">{placeLabel(draft.place)} <button type="button" onclick={() => (draft.place = null)}>×</button></div>
				{:else}
					<PlacePicker {search} onpick={(p) => (draft.place = p)} />
				{/if}
				<div class="pairs">
					<label>Kč<input type="number" bind:value={draft.minPrice} placeholder="from" /><input type="number" bind:value={draft.maxPrice} placeholder="to" /></label>
					<label>m²<input type="number" bind:value={draft.minSize} placeholder="from" /></label>
					<label>land m²<input type="number" bind:value={draft.minLand} placeholder="from" /></label>
					<label>rooms<input type="number" min="1" max="9" bind:value={draft.minRooms} placeholder="1" /><input type="number" min="1" max="9" bind:value={draft.maxRooms} placeholder="9" /></label>
					<label>kitchen
						<select bind:value={draft.kitchen}><option value={null}>any</option><option value="kitchenette">+kk</option><option value="separate">+1</option></select>
					</label>
				</div>
			{/if}
		{/if}
	</section>

	<section class:open={openSection === 'portals'}>
		<button type="button" class="section__head" onclick={() => (openSection = 'portals')}>
			Portals <span class="count">{draft.portals.length}/{PORTALS.length}</span>
		</button>
		{#if openSection === 'portals'}
			<div class="seg">
				{#each PORTALS as portal (portal)}
					<button type="button" class:on={draft.portals.includes(portal)} onclick={() => togglePortal(portal)}>{PORTAL_LABEL[portal]}</button>
				{/each}
			</div>
		{/if}
	</section>

	<section class:open={openSection === 'scoring'}>
		<button type="button" class="section__head" onclick={() => (openSection = 'scoring')}>Scoring</button>
		{#if openSection === 'scoring'}
			<div class="split" title="How a top score splits between your wishes">
				{#each split as part, i (part.label)}
					{#if part.weight > 0}
						<span style="flex: {part.weight}; background: {SHADES[i]}">{part.label} {total ? Math.round((100 * part.weight) / total) : 0}%</span>
					{/if}
				{/each}
				{#if total === 0}<span class="split__empty">No wishes yet. Every listing scores the same.</span>{/if}
			</div>
			<div class="slider"><span>Price per m²</span><input type="range" min="0" max="50" bind:value={draft.pricePerM2Weight} /><b>{draft.pricePerM2Weight}</b></div>
			<div class="slider"><span>Price</span><input type="range" min="0" max="50" bind:value={draft.priceWeight} /><b>{draft.priceWeight}</b></div>
			{#if draft.priceWeight > 0}<label class="sub">good up to <input type="number" bind:value={draft.maxGoodPrice} /> Kč</label>{/if}
			<div class="slider"><span>Size</span><input type="range" min="0" max="50" bind:value={draft.sizeWeight} /><b>{draft.sizeWeight}</b></div>
			{#if draft.sizeWeight > 0}<label class="sub">ideal <input type="number" bind:value={draft.idealSize} /> m²</label>{/if}
			<div class="slider"><span>Land</span><input type="range" min="0" max="50" bind:value={draft.landWeight} /><b>{draft.landWeight}</b></div>
			{#if draft.landWeight > 0}<label class="sub">ideal <input type="number" bind:value={draft.idealLand} /> m²</label>{/if}
			<div class="slider"><span>Layout</span><input type="range" min="0" max="50" bind:value={draft.dispositionWeight} /><b>{draft.dispositionWeight}</b></div>
			{#if draft.dispositionWeight > 0}
				<div class="sub codes">
					{#each DISPOSITIONS as code (code)}
						<button type="button" class:on={draft.preferredDispositions.includes(code)} onclick={() => toggleDisposition(code)}>
							{#if draft.preferredDispositions.includes(code)}{draft.preferredDispositions.indexOf(code) + 1}·{/if}{code}
						</button>
					{/each}
				</div>
			{/if}
			<div class="slider"><span>Place</span><input type="range" min="0" max="50" bind:value={draft.placeWeight} /><b>{draft.placeWeight}</b></div>
			{#if draft.placeWeight > 0}
				<div class="sub">
					{#each draft.preferredPlaces as place, i (place.kind + place.code)}
						<div class="chip">{i + 1}. {placeLabel(place)} <button type="button" onclick={() => draft.preferredPlaces.splice(i, 1)}>×</button></div>
					{/each}
					<PlacePicker {search} within={draft.place} placeholder="Add a place inside the search" onpick={(p) => draft.preferredPlaces.push(p)} />
				</div>
			{/if}
		{/if}
	</section>

	<footer class="drawer__foot">
		<button type="button" class="ghost" onclick={oncancel}>Cancel</button>
		<button type="button" class="primary" onclick={onsave}>{editing ? 'Save' : 'Create'}</button>
	</footer>
</aside>

<style>
	.scrim { position: fixed; inset: 0; background: rgb(0 0 0 / 0.25); z-index: 20; }
	.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(30rem, 92vw); z-index: 21; background: var(--color-ground); border-left: 1px solid var(--color-line); display: flex; flex-direction: column; overflow-y: auto; box-shadow: -8px 0 24px rgb(0 0 0 / 0.15); }
	.drawer__head { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-4); border-bottom: 1px solid var(--color-line); }
	.title { flex: 1; font-size: 1.125rem; font-weight: 600; border: none; background: none; color: inherit; border-bottom: 1px dashed var(--color-line); }
	.switch { font-size: 0.8125rem; white-space: nowrap; }
	.menu { position: relative; }
	.menu > button { background: none; border: none; color: inherit; font-size: 1.25rem; cursor: pointer; }
	.menu__pop { position: absolute; right: 0; top: 100%; background: var(--color-card); border: 1px solid var(--color-line); border-radius: var(--radius-md); padding: var(--space-1); }
	.menu__pop button { background: none; border: none; color: var(--color-bronze); padding: var(--space-2) var(--space-3); white-space: nowrap; cursor: pointer; }
	.preview { display: flex; flex-wrap: wrap; gap: var(--space-1); padding: var(--space-3) var(--space-4); background: var(--color-card); border-bottom: 1px solid var(--color-line); }
	.preview__tab { font-weight: 700; margin-right: var(--space-2); }
	.preview__chip { font-size: 0.75rem; border: 1px solid var(--color-line); border-radius: var(--radius-full); padding: 0 var(--space-2); }
	section { border-bottom: 1px solid var(--color-line); padding: 0 var(--space-4); }
	section.open { padding-bottom: var(--space-4); }
	.section__head { width: 100%; text-align: left; background: none; border: none; color: inherit; font-weight: 700; padding: var(--space-3) 0; cursor: pointer; display: flex; gap: var(--space-2); align-items: center; }
	.lock, .count { font-size: 0.6875rem; font-weight: 400; color: var(--color-bronze); border: 1px solid var(--color-line); border-radius: var(--radius-full); padding: 0 var(--space-2); }
	.seg { display: flex; gap: 0; margin-bottom: var(--space-2); }
	.seg button, .codes button { border: 1px solid var(--color-line); background: var(--color-card); color: inherit; padding: var(--space-1) var(--space-3); cursor: pointer; font-size: 0.8125rem; }
	.seg button:first-child { border-radius: var(--radius-md) 0 0 var(--radius-md); }
	.seg button:last-child { border-radius: 0 var(--radius-md) var(--radius-md) 0; }
	.seg .on, .codes .on { background: var(--color-olive); color: var(--color-ground); }
	.pairs { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-2); margin-top: var(--space-2); }
	.pairs label { display: flex; gap: var(--space-1); align-items: center; font-size: 0.75rem; color: var(--color-bronze); }
	.pairs input, .pairs select { width: 5rem; }
	.split { display: flex; height: 1.75rem; border-radius: var(--radius-md); overflow: hidden; margin: var(--space-2) 0 var(--space-3); border: 1px solid var(--color-line); }
	.split span { display: flex; align-items: center; justify-content: center; font-size: 0.6875rem; color: var(--color-ground); white-space: nowrap; overflow: hidden; }
	.split .split__empty { flex: 1; color: var(--color-bronze); }
	.slider { display: grid; grid-template-columns: 6.5rem 1fr 2rem; align-items: center; gap: var(--space-2); font-size: 0.875rem; }
	.slider b { text-align: right; font-variant-numeric: tabular-nums; }
	.sub { display: block; margin: 0 0 var(--space-2) 6.5rem; font-size: 0.8125rem; }
	.sub input[type='number'] { width: 6rem; }
	.codes { display: flex; flex-wrap: wrap; gap: 2px; }
	.codes button { border-radius: var(--radius-full); padding: 0 var(--space-2); }
	.chip { display: flex; justify-content: space-between; gap: var(--space-2); font-size: 0.8125rem; padding: var(--space-1) 0; }
	.chip button { background: none; border: none; color: var(--color-bronze); cursor: pointer; }
	.drawer__foot { margin-top: auto; display: flex; justify-content: flex-end; gap: var(--space-2); padding: var(--space-3) var(--space-4); border-top: 1px solid var(--color-line); background: var(--color-card); position: sticky; bottom: 0; }
	.ghost { background: none; border: 1px solid var(--color-line); color: inherit; border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); cursor: pointer; }
	.primary { background: var(--color-amber); color: var(--color-on-amber); border: none; border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); font-weight: 600; cursor: pointer; }
	.hint { color: var(--color-bronze); font-size: 0.8125rem; }
</style>
