<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError, type NamedPlace, type PlaceRef } from '$lib/api/client';
	import { errorMessage } from '$lib/errors';
	import LayoutChips from '$lib/forms/LayoutChips.svelte';
	import PortalTiles from '$lib/forms/PortalTiles.svelte';
	import RangeSlider from '$lib/forms/RangeSlider.svelte';
	import ValueSlider from '$lib/forms/ValueSlider.svelte';
	import { LAND_SCALE, priceScale, SIZE_SCALE } from '$lib/forms/scale';
	import { getTranslatorContext } from '$lib/i18n/context';
	import SearchPlacePicker from '$lib/map/SearchPlacePicker.svelte';
	import ScoringSection from '$lib/scoring/ScoringSection.svelte';
	import type { ProfileDraft, Search } from './profile-draft.svelte';
	import SearchSummary from './SearchSummary.svelte';

	/* The window in front of the inbox that creates a profile, or edits and
	deletes a stored one. A stored profile's search is fixed and only shown.
	Saving and deleting are the caller's, which may refuse with a reason. */
	let {
		draft,
		stored,
		searchPlaces,
		onsave,
		ondelete,
		oncancel
	}: {
		draft: ProfileDraft;
		stored: boolean;
		searchPlaces: (query: string, within?: PlaceRef, kinds?: PlaceRef['kind'][]) => Promise<NamedPlace[]>;
		onsave: () => Promise<void>;
		ondelete: () => Promise<void>;
		oncancel: () => void;
	} = $props();

	const t = getTranslatorContext();

	const OFFER_TYPES: readonly Search['offer_type'][] = ['rent', 'sale'];
	const ESTATE_TYPES: readonly Search['estate_type'][] = ['flat', 'house', 'cottage', 'land'];

	let dialog = $state<HTMLElement>();
	let busy = $state(false);
	let failure = $state<string | null>(null);
	let confirmingDelete = $state(false);

	const hasSize = $derived(draft.search.estate_type !== 'land');
	const hasLand = $derived(draft.search.estate_type !== 'flat');
	const missingHint = $derived.by(() => {
		if (draft.missing.includes('name')) return t.t('Name the profile.');
		if (draft.missing.includes('place')) return t.t('Pick where to search.');
		if (draft.missing.includes('portals')) return t.t('Pick at least one portal.');
		return '';
	});

	async function run(action: () => Promise<void>, failed: (reason: string) => string): Promise<void> {
		busy = true;
		failure = null;
		try {
			await action();
		} catch (error) {
			// The sidecar's reason is meant for a developer, so it only follows
			// the user's own message.
			const reason = error instanceof ApiError && error.reason !== null ? error.reason : errorMessage(error);
			failure = failed(reason);
		} finally {
			busy = false;
		}
	}

	function save(): Promise<void> {
		return run(onsave, (reason) => t.t('Could not save the profile: {reason}', { reason }));
	}

	function remove(): Promise<void> {
		return run(ondelete, (reason) => t.t('Could not delete the profile: {reason}', { reason }));
	}

	function offerName(offerType: Search['offer_type']): string {
		return offerType === 'rent' ? t.t('Rent') : t.t('Buy');
	}

	function estateName(estateType: Search['estate_type']): string {
		if (estateType === 'flat') return t.t('Flat');
		if (estateType === 'house') return t.t('House');
		if (estateType === 'cottage') return t.t('Cottage');
		return t.t('Land');
	}

	function close(): void {
		if (!busy) oncancel();
	}

	// An Escape a control inside already used, such as closing the place
	// search's list, leaves the window open.
	function onkeydown(event: KeyboardEvent): void {
		if (event.key !== 'Escape' || event.defaultPrevented) return;
		if (confirmingDelete) confirmingDelete = false;
		else close();
	}

	onMount(() => dialog?.focus());
</script>

<svelte:window {onkeydown} />

<div class="profile-editor__backdrop" role="presentation" onclick={close}></div>

<div
	class="profile-editor"
	role="dialog"
	aria-modal="true"
	aria-labelledby="profile-editor-title"
	tabindex="-1"
	bind:this={dialog}
>
	<header class="profile-editor__head">
		<h2 class="profile-editor__title" id="profile-editor-title">{stored ? t.t('Edit profile') : t.t('New profile')}</h2>
		{#if stored}
			<label class="profile-editor__watching">
				<input type="checkbox" checked={!draft.paused} onchange={() => (draft.paused = !draft.paused)} />
				{draft.paused ? t.t('Paused') : t.t('Watching')}
			</label>
		{/if}
		<button type="button" class="profile-editor__close" aria-label={t.t('Close')} onclick={close}>×</button>
	</header>

	<div class="profile-editor__body">
		<section class="profile-editor__section">
			<label class="profile-editor__name">
				<span class="profile-editor__label">{t.t('Name')}</span>
				<input
					class="profile-editor__name-input"
					bind:value={draft.name}
					placeholder={t.t('e.g. Praha 7 flats')}
				/>
			</label>
		</section>

		<section class="profile-editor__section">
			<h3 class="profile-editor__heading">{t.t('What are you looking for?')}</h3>
			{#if stored && draft.place !== null}
				<SearchSummary search={draft.search} place={draft.place} />
			{:else}
				<div class="profile-editor__choices">
					<div class="profile-editor__segments" role="group" aria-label={t.t('Rent or buy')}>
						{#each OFFER_TYPES as offerType (offerType)}
							<button
								type="button"
								class="profile-editor__segment"
								class:profile-editor__segment--on={draft.search.offer_type === offerType}
								aria-pressed={draft.search.offer_type === offerType}
								onclick={() => draft.setOfferType(offerType)}>{offerName(offerType)}</button
							>
						{/each}
					</div>
					<div class="profile-editor__segments" role="group" aria-label={t.t('Type of property')}>
						{#each ESTATE_TYPES as estateType (estateType)}
							<button
								type="button"
								class="profile-editor__segment"
								class:profile-editor__segment--on={draft.search.estate_type === estateType}
								aria-pressed={draft.search.estate_type === estateType}
								onclick={() => (draft.search = { ...draft.search, estate_type: estateType })}
								>{estateName(estateType)}</button
							>
						{/each}
					</div>
				</div>
			{/if}
		</section>

		{#if !stored}
			<section class="profile-editor__section">
				<h3 class="profile-editor__heading">{t.t('Where?')}</h3>
				<SearchPlacePicker
					search={searchPlaces}
					place={draft.place}
					onchange={(place) => draft.setPlace(place)}
				/>
			</section>

			<section class="profile-editor__section">
				<h3 class="profile-editor__heading">{t.t('Limits')}</h3>
				<div class="profile-editor__limits">
					<span class="profile-editor__limit">
						{draft.search.offer_type === 'rent' ? t.t('Monthly rent') : t.t('Price')}
					</span>
					<div>
						<RangeSlider
							scale={priceScale(draft.search.offer_type)}
							bind:low={draft.search.min_price}
							bind:high={draft.search.max_price}
							name={t.t('Price')}
							unit="Kč"
						/>
						{#if draft.crossedRanges.includes('price')}
							<p class="profile-editor__problem">{t.t('The lowest price is above the highest.')}</p>
						{/if}
					</div>
					{#if hasSize}
						<span class="profile-editor__limit">{t.t('Size')}</span>
						<div>
							<RangeSlider
								scale={SIZE_SCALE}
								bind:low={draft.search.min_size_m2}
								bind:high={draft.search.max_size_m2}
								name={t.t('Size')}
								unit="m²"
							/>
							{#if draft.crossedRanges.includes('size')}
								<p class="profile-editor__problem">{t.t('The smallest size is above the largest.')}</p>
							{/if}
						</div>
					{/if}
					{#if hasLand}
						<span class="profile-editor__limit">{t.t('Land at least')}</span>
						<ValueSlider
							scale={LAND_SCALE}
							bind:value={draft.search.min_land_m2}
							name={t.t('Land at least')}
							unit="m²"
							placeholder={t.t('any')}
						/>
					{/if}
					{#if hasSize}
						<span class="profile-editor__limit">{t.t('Layout')}</span>
						<div>
							<LayoutChips bind:selected={draft.search.dispositions} name={t.t('Accepted layouts')} />
							<p class="profile-editor__hint">
								{draft.search.dispositions.length === 0
									? t.t('Any layout. Pick some to show only those.')
									: t.t('Only the picked layouts.')}
							</p>
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<section class="profile-editor__section">
			<h3 class="profile-editor__heading">{t.t('Portals')}</h3>
			<PortalTiles bind:selected={draft.portals} name={t.t('Portals')} />
		</section>

		<section class="profile-editor__section">
			<h3 class="profile-editor__heading">{t.t('What matters most?')}</h3>
			<ScoringSection
				criteria={draft.search}
				searchPlace={draft.place}
				bind:preferredValues={draft.preferredValues}
				bind:weights={draft.weights}
				{searchPlaces}
			/>
		</section>
	</div>

	<footer class="profile-editor__foot">
		{#if stored}
			{#if confirmingDelete}
				<span class="profile-editor__confirm">
					{t.t('Delete “{name}”? This cannot be undone.', { name: draft.name })}
				</span>
				<button type="button" class="profile-editor__danger" disabled={busy} onclick={remove}>
					{t.t('Delete')}
				</button>
				<button type="button" class="profile-editor__ghost" onclick={() => (confirmingDelete = false)}>
					{t.t('Keep it')}
				</button>
			{:else}
				<button type="button" class="profile-editor__delete" onclick={() => (confirmingDelete = true)}>
					{t.t('Delete profile')}
				</button>
			{/if}
		{/if}
		<span class="profile-editor__status" role="status">{missingHint !== '' ? missingHint : (failure ?? '')}</span>
		<button type="button" class="profile-editor__ghost" disabled={busy} onclick={close}>{t.t('Cancel')}</button>
		<button type="button" class="profile-editor__save" disabled={busy || !draft.canSave} onclick={save}>
			{stored ? t.t('Save changes') : t.t('Create profile')}
		</button>
	</footer>
</div>

<style>
	.profile-editor__backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		background: color-mix(in srgb, var(--color-ground) 70%, transparent);
		backdrop-filter: blur(2px);
	}

	.profile-editor {
		position: fixed;
		top: 4vh;
		bottom: 4vh;
		left: 50%;
		z-index: 41;
		display: flex;
		flex-direction: column;
		width: min(66rem, 94vw);
		overflow: hidden;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-ground);
		box-shadow: 0 24px 64px color-mix(in srgb, var(--color-olive) 25%, transparent);
		transform: translateX(-50%);
	}

	/* The window takes focus when it opens, to bring the keyboard into it,
	without a ring around all of it. */
	.profile-editor:focus {
		outline: none;
	}

	.profile-editor__head {
		display: flex;
		align-items: center;
		gap: var(--space-3);
		padding: var(--space-3) var(--space-6);
		border-bottom: 1px solid var(--color-line);
	}

	.profile-editor__title {
		flex: 1;
		margin: 0;
		font-size: 1.125rem;
	}

	.profile-editor__watching {
		display: inline-flex;
		align-items: center;
		gap: var(--space-2);
		font-size: 0.875rem;
	}

	.profile-editor__close {
		border: none;
		background: none;
		color: var(--color-bronze);
		font-size: 1.5rem;
		cursor: pointer;
	}

	.profile-editor__body {
		flex: 1;
		overflow-y: auto;
		padding: 0 var(--space-6) var(--space-6);
	}

	.profile-editor__section {
		padding: var(--space-4) 0;
		border-bottom: 1px solid var(--color-line);
	}

	.profile-editor__section:last-child {
		border-bottom: none;
	}

	.profile-editor__heading {
		margin: 0 0 var(--space-3);
		font-size: 1rem;
	}

	.profile-editor__name {
		display: flex;
		align-items: center;
		gap: var(--space-4);
	}

	.profile-editor__label {
		width: 8rem;
		font-weight: 700;
	}

	.profile-editor__name-input {
		flex: 1;
		max-width: 32rem;
		padding: var(--space-2) var(--space-4);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-card);
		color: inherit;
		font-size: 1.0625rem;
		font-weight: 600;
	}

	.profile-editor__name-input:focus {
		border-color: var(--color-olive);
		outline: none;
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-olive) 25%, transparent);
	}

	.profile-editor__choices {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-4);
	}

	.profile-editor__segments {
		display: inline-flex;
	}

	.profile-editor__segment {
		margin-left: -1px;
		padding: var(--space-2) var(--space-4);
		border: 1px solid var(--color-line);
		background: var(--color-card);
		color: inherit;
		font-weight: 600;
		cursor: pointer;
	}

	.profile-editor__segment:first-child {
		margin-left: 0;
		border-radius: var(--radius-md) 0 0 var(--radius-md);
	}

	.profile-editor__segment:last-child {
		border-radius: 0 var(--radius-md) var(--radius-md) 0;
	}

	.profile-editor__segment--on {
		position: relative;
		border-color: var(--color-olive);
		background: var(--color-olive);
		color: var(--color-ground);
	}

	.profile-editor__limits {
		display: grid;
		grid-template-columns: 8rem 1fr;
		gap: var(--space-4);
		align-items: center;
	}

	.profile-editor__limit {
		align-self: start;
		padding-top: var(--space-1);
		font-size: 0.875rem;
		font-weight: 600;
	}

	.profile-editor__hint,
	.profile-editor__problem {
		margin: var(--space-2) 0 0;
		font-size: 0.8125rem;
	}

	.profile-editor__hint {
		color: var(--color-bronze);
	}

	.profile-editor__problem {
		color: var(--color-amber);
		font-weight: 600;
	}

	.profile-editor__foot {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-6);
		border-top: 1px solid var(--color-line);
		background: var(--color-card);
	}

	.profile-editor__status {
		flex: 1;
		color: var(--color-bronze);
		font-size: 0.875rem;
		text-align: right;
	}

	.profile-editor__confirm {
		font-size: 0.875rem;
	}

	.profile-editor__ghost {
		padding: var(--space-2) var(--space-4);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: none;
		color: inherit;
		cursor: pointer;
	}

	.profile-editor__save {
		padding: var(--space-2) var(--space-6);
		border: none;
		border-radius: var(--radius-md);
		background: var(--color-amber);
		color: var(--color-on-amber);
		font-weight: 700;
		cursor: pointer;
	}

	.profile-editor__save:disabled,
	.profile-editor__ghost:disabled,
	.profile-editor__danger:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}

	.profile-editor__delete {
		border: none;
		background: none;
		color: var(--color-bronze);
		text-decoration: underline;
		cursor: pointer;
	}

	.profile-editor__danger {
		padding: var(--space-2) var(--space-4);
		border: none;
		border-radius: var(--radius-md);
		background: var(--color-bronze);
		color: var(--color-ground);
		font-weight: 600;
		cursor: pointer;
	}
</style>
