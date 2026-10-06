<!-- PROTOTYPE, throwaway. Round 2 of the profile editor, from variant A: a
window in front of the dimmed inbox, sections top to bottom. -->
<script lang="ts">
	import CzechMapPicker from './CzechMapPicker.svelte';
	import LayoutChips from './LayoutChips.svelte';
	import PortalPicker from './PortalPicker.svelte';
	import RangeSlider from './RangeSlider.svelte';
	import ScoringSection from './ScoringSection.svelte';
	import { DISPOSITIONS, placeLabel, type Draft, type PlaceSearch } from './draft.svelte';
	import { kc, m2, priceStops, sizeStops, landStops } from './units';

	let {
		draft = $bindable(),
		editing,
		search,
		mapMode,
		onsave,
		oncancel,
		ondelete
	}: {
		draft: Draft;
		editing: boolean;
		search: PlaceSearch;
		mapMode: 'smooth' | 'spotlight' | 'free';
		onsave: () => void;
		oncancel: () => void;
		ondelete: () => void;
	} = $props();

	let confirmDelete = $state(false);

	const ESTATES = [
		{ value: 'flat', label: 'Flat' },
		{ value: 'house', label: 'House' },
		{ value: 'cottage', label: 'Cottage' },
		{ value: 'land', label: 'Land' }
	] as const;

	const canSave = $derived(draft.name.trim() !== '' && draft.place !== null && draft.portals.length > 0);

	function setOffer(offer: 'rent' | 'sale'): void {
		if (offer === draft.offerType) return;
		draft.offerType = offer;
		// Prices on another scale make no sense after the switch.
		draft.minPrice = null;
		draft.maxPrice = null;
		draft.maxGoodPrice = null;
	}

	function onkeydown(event: KeyboardEvent): void {
		if (event.key === 'Escape') oncancel();
	}
</script>

<svelte:window {onkeydown} />

<div class="backdrop" role="presentation" onclick={oncancel}></div>

<div class="window" role="dialog" aria-modal="true" aria-label={editing ? 'Edit profile' : 'New profile'}>
	<header class="head">
		<h2 class="title">{editing ? 'Edit profile' : 'New profile'}</h2>
		{#if editing}
			<label class="pause">
				<input type="checkbox" checked={!draft.paused} onchange={() => (draft.paused = !draft.paused)} />
				<span>{draft.paused ? 'Paused' : 'Watching'}</span>
			</label>
		{/if}
		<button type="button" class="close" aria-label="Close" onclick={oncancel}>×</button>
	</header>

	<div class="body">
		<section class="naming">
			<label>
				<span class="naming__label">Name</span>
				<input class="name" bind:value={draft.name} placeholder="e.g. Praha 7 byty" />
			</label>
		</section>

		<section>
			<h3>What are you looking for?</h3>
			{#if editing}
				<div class="locked">
					<p>
						<b>{draft.offerType === 'rent' ? 'Rent' : 'Buy'} a {draft.estateType}</b> in
						{draft.place ? placeLabel(draft.place) : ''}
						{#if draft.minPrice || draft.maxPrice}· {draft.minPrice ? kc(draft.minPrice) : 'any'} to {draft.maxPrice ? kc(draft.maxPrice) : 'any'}{/if}
						{#if draft.minSize}· from {m2(draft.minSize)}{/if}
						{#if draft.layouts.length}· {draft.layouts.join(', ')}{/if}
					</p>
					<small>🔒 The search is fixed once a profile exists, because the listings it found answer it. For a different search, create a new profile.</small>
				</div>
			{:else}
				<div class="row">
					<div class="seg">
						<button type="button" class:on={draft.offerType === 'rent'} onclick={() => setOffer('rent')}>Rent</button>
						<button type="button" class:on={draft.offerType === 'sale'} onclick={() => setOffer('sale')}>Buy</button>
					</div>
					<div class="seg">
						{#each ESTATES as estate (estate.value)}
							<button type="button" class:on={draft.estateType === estate.value} onclick={() => (draft.estateType = estate.value)}>{estate.label}</button>
						{/each}
					</div>
				</div>
			{/if}
		</section>

		{#if !editing}
			<section>
				<h3>Where?</h3>
				{#key mapMode}<CzechMapPicker bind:place={draft.place} {search} mode={mapMode} />{/key}
			</section>

			<section>
				<h3>Limits</h3>
				<div class="limits">
					<span class="limit__name">{draft.offerType === 'rent' ? 'Rent' : 'Price'}</span>
					<RangeSlider stops={priceStops(draft.offerType)} bind:low={draft.minPrice} bind:high={draft.maxPrice} unit="Kč" openLow="0" openHigh="no limit" />
					{#if draft.estateType !== 'land'}
						<span class="limit__name">Size</span>
						<RangeSlider stops={sizeStops} bind:low={draft.minSize} bind:high={draft.maxSize} unit="m²" openLow="0" openHigh="no limit" />
					{/if}
					{#if draft.estateType !== 'flat'}
						<span class="limit__name">Land at least</span>
						<RangeSlider single stops={landStops} bind:value={draft.minLand} unit="m²" unset="any" />
					{/if}
					{#if draft.estateType !== 'land'}
						<span class="limit__name">Layout</span>
						<div>
							<LayoutChips bind:selected={draft.layouts} options={DISPOSITIONS} />
							<p class="hint">{draft.layouts.length === 0 ? 'Any layout. Pick some to show only those.' : `Only ${draft.layouts.join(', ')}.`}</p>
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<section>
			<h3>Portals</h3>
			<PortalPicker bind:portals={draft.portals} />
		</section>

		<section>
			<h3>What matters most?</h3>
			<ScoringSection bind:draft {search} />
		</section>
	</div>

	<footer class="foot">
		{#if editing}
			{#if confirmDelete}
				<span class="confirm">Delete “{draft.name}”? Listings it found stay.</span>
				<button type="button" class="danger" onclick={ondelete}>Delete</button>
				<button type="button" class="ghost" onclick={() => (confirmDelete = false)}>Keep it</button>
			{:else}
				<button type="button" class="link-danger" onclick={() => (confirmDelete = true)}>Delete profile</button>
			{/if}
		{/if}
		<span class="spacer"></span>
		<button type="button" class="ghost" onclick={oncancel}>Cancel</button>
		<button type="button" class="primary" disabled={!canSave} onclick={onsave}>{editing ? 'Save changes' : 'Create profile'}</button>
	</footer>
</div>

<style>
	.backdrop { position: fixed; inset: 0; z-index: 40; background: rgb(30 28 24 / 0.55); backdrop-filter: blur(2px); }
	.window { position: fixed; z-index: 41; top: 4vh; bottom: 4vh; left: 50%; transform: translateX(-50%); width: min(66rem, 94vw); display: flex; flex-direction: column; background: var(--color-ground); border-radius: 0.75rem; box-shadow: 0 24px 64px rgb(0 0 0 / 0.35); overflow: hidden; }
	.head { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3) var(--space-6); border-bottom: 1px solid var(--color-line); }
	.title { flex: 1; margin: 0; font-size: 1.125rem; }
	.naming { padding-top: var(--space-6); }
	.naming label { display: flex; align-items: center; gap: var(--space-4); }
	.naming__label { font-weight: 700; width: 8rem; }
	.name { flex: 1; max-width: 32rem; font-size: 1.0625rem; font-weight: 600; background: var(--color-card); border: 1px solid var(--color-line); border-radius: var(--radius-full); padding: var(--space-2) var(--space-4); color: inherit; }
	.name:focus { outline: none; border-color: var(--color-olive); box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-olive) 25%, transparent); }
	.pause { display: inline-flex; gap: var(--space-2); align-items: center; font-size: 0.875rem; }
	.close { background: none; border: none; font-size: 1.5rem; color: var(--color-bronze); cursor: pointer; }
	.body { flex: 1; overflow-y: auto; padding: 0 var(--space-6) var(--space-6); }
	section { padding: var(--space-4) 0; border-bottom: 1px solid var(--color-line); }
	section:last-child { border-bottom: none; }
	h3 { margin: 0 0 var(--space-3); font-size: 1rem; }
	.row { display: flex; gap: var(--space-4); flex-wrap: wrap; }
	.seg { display: inline-flex; }
	.seg button { border: 1px solid var(--color-line); background: var(--color-card); color: inherit; padding: var(--space-2) var(--space-4); cursor: pointer; margin-left: -1px; font-weight: 600; }
	.seg button:first-child { border-radius: var(--radius-md) 0 0 var(--radius-md); }
	.seg button:last-child { border-radius: 0 var(--radius-md) var(--radius-md) 0; }
	.seg button.on { background: var(--color-olive); border-color: var(--color-olive); color: var(--color-ground); }
	.limits { display: grid; grid-template-columns: 8rem 1fr; gap: var(--space-4) var(--space-4); align-items: center; }
	.limit__name { font-weight: 600; font-size: 0.875rem; align-self: start; padding-top: var(--space-1); }
	.hint { margin: var(--space-2) 0 0; color: var(--color-bronze); font-size: 0.8125rem; }
	.locked { background: var(--color-card); border: 1px dashed var(--color-line); border-radius: var(--radius-md); padding: var(--space-3); }
	.locked p { margin: 0 0 var(--space-2); }
	.locked small { color: var(--color-bronze); }
	.foot { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3) var(--space-6); background: var(--color-card); border-top: 1px solid var(--color-line); }
	.spacer { flex: 1; }
	.ghost { background: none; border: 1px solid var(--color-line); color: inherit; border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); cursor: pointer; }
	.primary { background: var(--color-amber); color: var(--color-on-amber); border: none; border-radius: var(--radius-md); padding: var(--space-2) var(--space-6); font-weight: 700; cursor: pointer; }
	.primary:disabled { opacity: 0.45; cursor: not-allowed; }
	.link-danger { background: none; border: none; color: var(--color-bronze); text-decoration: underline; cursor: pointer; }
	.danger { background: var(--color-bronze); color: var(--color-ground); border: none; border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); font-weight: 600; cursor: pointer; }
	.confirm { font-size: 0.875rem; }
</style>
