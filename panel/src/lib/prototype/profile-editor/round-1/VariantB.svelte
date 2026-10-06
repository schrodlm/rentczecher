<!-- PROTOTYPE, throwaway. Round 1, unmounted. Variant B: a guided wizard that reads as a
sentence, with importance levels instead of raw weights. Editing skips the
search steps, which are fixed. -->
<script lang="ts" module>
	export const name = 'Guided steps';
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

	const STEPS = ['What', 'Where', 'Limits', 'What matters', 'Finish'];
	// svelte-ignore state_referenced_locally
	let step = $state(editing ? 3 : 0);

	const LEVELS = [
		{ label: 'Ignore', weight: 0 },
		{ label: 'A little', weight: 10 },
		{ label: 'Matters', weight: 25 },
		{ label: 'Most', weight: 50 }
	];

	type WeightKey = 'pricePerM2Weight' | 'priceWeight' | 'sizeWeight' | 'landWeight' | 'dispositionWeight' | 'placeWeight';
	const WISHES: { key: WeightKey; title: string; blurb: string }[] = [
		{ key: 'priceWeight', title: 'A good price', blurb: 'Cheaper than your good price scores higher.' },
		{ key: 'pricePerM2Weight', title: 'Value per m²', blurb: 'More space for the money scores higher.' },
		{ key: 'sizeWeight', title: 'The right size', blurb: 'Closer to your ideal size scores higher.' },
		{ key: 'landWeight', title: 'Enough land', blurb: 'Closer to your ideal land area scores higher.' },
		{ key: 'dispositionWeight', title: 'A layout you like', blurb: 'Your first choice scores highest.' },
		{ key: 'placeWeight', title: 'A spot you like', blurb: 'Your first place scores highest.' }
	];

	function levelOf(weight: number): number {
		let best = 0;
		LEVELS.forEach((level, i) => {
			if (Math.abs(level.weight - weight) < Math.abs(LEVELS[best].weight - weight)) best = i;
		});
		return best;
	}

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

	const firstStep = $derived(editing ? 3 : 0);
</script>

<div class="wizard">
	<ol class="steps">
		{#each STEPS as label, i (label)}
			<li class:current={i === step} class:locked={editing && i < 3}>
				<button type="button" disabled={editing && i < 3} onclick={() => (step = i)}>{i + 1}. {label}</button>
			</li>
		{/each}
	</ol>

	{#if editing}
		<p class="sentence locked-sentence">
			Looking to {draft.offerType === 'rent' ? 'rent' : 'buy'} a {draft.estateType} in
			<b>{draft.place ? placeLabel(draft.place) : '...'}</b>
			{#if draft.maxPrice}for up to {draft.maxPrice.toLocaleString('cs-CZ')} Kč{/if}.
			<small>This search is fixed. A different search is a new profile.</small>
		</p>
	{/if}

	<div class="card">
		{#if step === 0}
			<p class="sentence">
				I want to
				<select bind:value={draft.offerType}><option value="rent">rent</option><option value="sale">buy</option></select>
				a
				<select bind:value={draft.estateType}>
					<option value="flat">flat</option><option value="house">house</option>
					<option value="land">plot of land</option><option value="cottage">cottage</option>
				</select>
			</p>
		{:else if step === 1}
			<h3>Where should we look?</h3>
			{#if draft.place}
				<p class="big">{placeLabel(draft.place)} <button type="button" onclick={() => (draft.place = null)}>change</button></p>
			{:else}
				<PlacePicker {search} placeholder="A region, district, town, part of town or street" onpick={(p) => (draft.place = p)} />
				<p class="hint">Pick from the list. Only real places can be chosen.</p>
			{/if}
		{:else if step === 2}
			<p class="sentence">
				Priced between <input type="number" bind:value={draft.minPrice} placeholder="any" /> and
				<input type="number" bind:value={draft.maxPrice} placeholder="any" /> Kč,
				at least <input type="number" bind:value={draft.minSize} placeholder="any" /> m²,
				{#if draft.estateType !== 'flat'}with at least <input type="number" bind:value={draft.minLand} placeholder="any" /> m² of land,{/if}
				from <input type="number" min="1" max="9" bind:value={draft.minRooms} placeholder="1" /> to
				<input type="number" min="1" max="9" bind:value={draft.maxRooms} placeholder="9" /> rooms,
				kitchen
				<select bind:value={draft.kitchen}>
					<option value={null}>either way</option><option value="kitchenette">as a kitchenette</option>
					<option value="separate">as its own room</option>
				</select>.
			</p>
			<p class="hint">Leave a field empty for no limit.</p>
		{:else if step === 3}
			<h3>What matters to you?</h3>
			<p class="hint">This only orders what you see. Nothing gets hidden.</p>
			<div class="wishes">
				{#each WISHES as wish (wish.key)}
					<div class="wish" class:wish--on={draft[wish.key] > 0}>
						<strong>{wish.title}</strong>
						<span class="hint">{wish.blurb}</span>
						<div class="levels">
							{#each LEVELS as level, i (level.label)}
								<button type="button" class:on={levelOf(draft[wish.key]) === i} onclick={() => (draft[wish.key] = level.weight)}>{level.label}</button>
							{/each}
						</div>
						{#if draft[wish.key] > 0}
							{#if wish.key === 'priceWeight'}
								<label>Good price up to <input type="number" bind:value={draft.maxGoodPrice} /> Kč</label>
							{:else if wish.key === 'sizeWeight'}
								<label>Ideal size <input type="number" bind:value={draft.idealSize} /> m²</label>
							{:else if wish.key === 'landWeight'}
								<label>Ideal land <input type="number" bind:value={draft.idealLand} /> m²</label>
							{:else if wish.key === 'dispositionWeight'}
								<div class="codes">
									{#each DISPOSITIONS as code (code)}
										<button type="button" class="code" class:on={draft.preferredDispositions.includes(code)} onclick={() => toggleDisposition(code)}>
											{#if draft.preferredDispositions.includes(code)}{draft.preferredDispositions.indexOf(code) + 1}.{/if} {code}
										</button>
									{/each}
								</div>
							{:else if wish.key === 'placeWeight'}
								{#each draft.preferredPlaces as place, i (place.kind + place.code)}
									<div>{i + 1}. {placeLabel(place)} <button type="button" onclick={() => draft.preferredPlaces.splice(i, 1)}>×</button></div>
								{/each}
								<PlacePicker {search} within={draft.place} placeholder="Add a place inside your search" onpick={(p) => draft.preferredPlaces.push(p)} />
							{/if}
						{/if}
					</div>
				{/each}
			</div>
		{:else}
			<h3>Last touches</h3>
			<label class="block">Call it <input bind:value={draft.name} placeholder="Praha 7 byty" /></label>
			<p>Look on
				{#each PORTALS as portal (portal)}
					<label class="inline"><input type="checkbox" checked={draft.portals.includes(portal)} onchange={() => togglePortal(portal)} /> {PORTAL_LABEL[portal]}</label>
				{/each}
			</p>
			{#if editing}
				<label class="block"><input type="checkbox" bind:checked={draft.paused} /> Pause this profile (scans skip it)</label>
				<p><button type="button" class="link-danger" onclick={ondelete}>Delete this profile</button></p>
			{/if}
		{/if}
	</div>

	<footer class="nav">
		<button type="button" onclick={oncancel}>Cancel</button>
		<span class="spacer"></span>
		{#if step > firstStep}<button type="button" onclick={() => step--}>Back</button>{/if}
		{#if step < STEPS.length - 1}
			<button type="button" class="primary" onclick={() => step++}>Next</button>
		{:else}
			<button type="button" class="primary" onclick={onsave}>{editing ? 'Save' : 'Start watching'}</button>
		{/if}
	</footer>
</div>

<style>
	.wizard { max-width: 44rem; margin: var(--space-6) auto; padding: 0 var(--space-4) 4rem; }
	.steps { display: flex; gap: var(--space-2); list-style: none; padding: 0; margin: 0 0 var(--space-4); }
	.steps button { background: none; border: none; color: var(--color-bronze); cursor: pointer; padding: var(--space-1) 0; font-size: 0.875rem; }
	.steps .current button { color: var(--color-ink); font-weight: 700; border-bottom: 2px solid var(--color-amber); }
	.steps .locked button { opacity: 0.4; cursor: default; }
	.card { background: var(--color-card); border: 1px solid var(--color-line); border-radius: var(--radius-md); padding: var(--space-6); min-height: 14rem; }
	.sentence { font-size: 1.25rem; line-height: 2.4; margin: 0; }
	.sentence input { width: 6.5rem; font-size: 1rem; }
	.sentence select { font-size: 1rem; }
	.locked-sentence { font-size: 1rem; line-height: 1.6; margin-bottom: var(--space-3); }
	.locked-sentence small { display: block; color: var(--color-bronze); }
	.big { font-size: 1.25rem; }
	.big button { font-size: 0.8125rem; }
	.hint { color: var(--color-bronze); font-size: 0.8125rem; }
	.wishes { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3); }
	.wish { border: 1px solid var(--color-line); border-radius: var(--radius-md); padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-2); }
	.wish--on { border-color: var(--color-olive); }
	.levels { display: flex; gap: var(--space-1); }
	.levels button, .code { border: 1px solid var(--color-line); background: var(--color-ground); color: inherit; border-radius: var(--radius-full); padding: 0 var(--space-2); cursor: pointer; font-size: 0.8125rem; }
	.levels .on, .code.on { background: var(--color-olive); color: var(--color-ground); }
	.codes { display: flex; flex-wrap: wrap; gap: var(--space-1); }
	.block { display: block; margin: var(--space-3) 0; }
	.inline { margin-left: var(--space-3); }
	.nav { display: flex; gap: var(--space-2); margin-top: var(--space-4); }
	.spacer { flex: 1; }
	.nav button { background: none; border: 1px solid var(--color-line); color: inherit; border-radius: var(--radius-md); padding: var(--space-2) var(--space-4); cursor: pointer; }
	.nav .primary { background: var(--color-amber); color: var(--color-on-amber); border: none; font-weight: 600; }
	.link-danger { background: none; border: none; color: var(--color-bronze); text-decoration: underline; cursor: pointer; padding: 0; }
</style>
