<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import logo from '$lib/assets/logo.svg';
	import { SidecarClient } from '$lib/api/client';
	import { sidecarConnection } from '$lib/api/connection';
	import { onEngineStopped } from '$lib/api/engine';
	import type { TrackedPropertyModel, PortalHealthModel, PostingPricesModel, ProfileModel } from '$lib/api/client';
	import { errorMessage } from '$lib/errors';
	import InboxHeader from '$lib/components/InboxHeader.svelte';
	import { ProfileDraft } from '$lib/editor/profile-draft.svelte';
	import ProfileEditor from '$lib/editor/ProfileEditor.svelte';
	import FeedbackButton from '$lib/components/FeedbackButton.svelte';
	import FeedbackDialog from '$lib/components/FeedbackDialog.svelte';
	import Inbox from '$lib/components/Inbox.svelte';
	import LanguageToggle from '$lib/components/LanguageToggle.svelte';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { keepSelection, takeKeptSelection } from '$lib/kept-selection';
	import { NearbyStore } from '$lib/nearby/nearby-store.svelte';
	import { OverpassClient } from '$lib/nearby/overpass';
	import { GalleryStore } from '$lib/stores/gallery.svelte';
	import { RunProgressStore } from '$lib/stores/run-progress.svelte';
	import { applyTheme } from '$lib/theme';
	import { UserConfigFile, type Language, type Theme, type UserConfig } from '$lib/user-config';
	import WelcomeWizard from '$lib/welcome/WelcomeWizard.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const t = getTranslatorContext();
	const userConfigFile = new UserConfigFile();
	// svelte-ignore state_referenced_locally
	let userConfig = $state<UserConfig>(data.userConfig);
	// svelte-ignore state_referenced_locally
	let welcoming = $state(data.firstRun);
	// Built on mount, once the connection is known. Every use below runs
	// after that, from the mount sequence or from user actions.
	let client: SidecarClient;
	let engineStopped = $state(false);

	const runProgress = new RunProgressStore();
	let galleries = $state<GalleryStore | null>(null);
	const nearby = new NearbyStore(new OverpassClient());

	let profiles = $state<ProfileModel[] | null>(null);
	let profilesError = $state<string | null>(null);
	let selectedProfileId = $state<string | null>(null);
	let selectedPropertyId = $state<string | null>(null);
	let health = $state<PortalHealthModel[]>([]);
	let runError = $state<string | null>(null);
	let listings = $state<TrackedPropertyModel[] | null>(null);
	let listingsError = $state<string | null>(null);
	let newCounts = $state<Record<string, number>>({});
	// The profile open in the editor, with the id it is stored under, or null
	// for a new one.
	let editing = $state<{ draft: ProfileDraft; profileId: string | null } | null>(null);
	let writingFeedback = $state(false);

	// While no preference weighs anything every listing scores 0, which says
	// nothing, so listings go unscored.
	const scoring = $derived.by(() => {
		const preferences = profiles?.find((profile) => profile.id === selectedProfileId)?.preferences;
		if (preferences === undefined) return null;
		const weighed =
			preferences.price_per_m2_weight +
			preferences.disposition_weight +
			preferences.size_weight +
			preferences.place_weight +
			preferences.land_weight +
			preferences.price_weight;
		return weighed > 0 ? preferences : null;
	});

	const newListings = $derived((listings ?? []).filter((l) => l.viewed_at === null));

	async function loadListings(profileId: string): Promise<void> {
		listingsError = null;
		try {
			const fetched = await client.listTrackedProperties(profileId, 'all');
			// A slow response for a tab the user already left must not
			// overwrite the tab they are on.
			if (profileId !== selectedProfileId) return;
			listings = fetched;
		} catch (err) {
			if (profileId !== selectedProfileId) return;
			listingsError = errorMessage(err);
		}
	}

	async function loadPriceHistory(propertyId: string): Promise<PostingPricesModel[]> {
		if (selectedProfileId === null) return [];
		return client.priceHistory(selectedProfileId, propertyId);
	}

	async function loadAllNewCounts(profileList: ProfileModel[]): Promise<void> {
		const others = profileList.filter((profile) => profile.id !== selectedProfileId);
		const counts = await Promise.all(
			others.map(async (profile) => {
				try {
					const newOnes = await client.listTrackedProperties(profile.id, 'new');
					return [profile.id, newOnes.length] as const;
				} catch {
					return [profile.id, 0] as const;
				}
			})
		);
		newCounts = { ...newCounts, ...Object.fromEntries(counts) };
	}

	async function handleViewed(propertyId: string): Promise<void> {
		if (selectedProfileId === null) return;
		try {
			await client.markViewed(selectedProfileId, propertyId);
		} catch {
			// A failed PATCH is not retried, the listing stays new until the
			// next reload.
			return;
		}
		const marked = listings?.find((l) => l.id === propertyId);
		if (marked && marked.viewed_at === null) {
			marked.viewed_at = new Date().toISOString();
		}
	}

	async function handleFavourite(propertyId: string, favourite: boolean): Promise<void> {
		if (selectedProfileId === null) return;
		try {
			if (favourite) await client.markFavourite(selectedProfileId, propertyId);
			else await client.clearFavourite(selectedProfileId, propertyId);
		} catch {
			// A failed favourite is not retried, the star stays as it was.
			return;
		}
		const marked = listings?.find((l) => l.id === propertyId);
		if (marked === undefined) return;
		const now = new Date().toISOString();
		marked.favourited_at = favourite ? now : null;
		marked.viewed_at = marked.viewed_at ?? now;
	}

	async function handleMarkAllViewed(propertyIds: string[]): Promise<void> {
		if (selectedProfileId === null) return;
		const profileId = selectedProfileId;
		await Promise.all(propertyIds.map((propertyId) => client.markViewed(profileId, propertyId).catch(() => {})));
		await loadListings(profileId);
	}

	async function loadHealth(): Promise<void> {
		try {
			health = await client.health();
		} catch {
			health = [];
		}
	}

	function selectProfile(profileId: string): void {
		if (profileId === selectedProfileId) return;
		if (selectedProfileId !== null) {
			newCounts = { ...newCounts, [selectedProfileId]: newListings.length };
		}
		selectedProfileId = profileId;
		selectedPropertyId = null;
		listings = null;
		void loadListings(profileId);
		runProgress.connect(client.eventsUrl(), profileId, () => {
			void loadListings(profileId);
			void loadHealth();
		});
	}

	function openNewProfile(): void {
		editing = { draft: ProfileDraft.blank(), profileId: null };
	}

	function openStoredProfile(profile: ProfileModel): void {
		editing = { draft: ProfileDraft.of(profile), profileId: profile.id };
	}

	async function saveProfile(): Promise<void> {
		if (editing === null || profiles === null) return;
		const { draft, profileId } = editing;
		if (profileId === null) {
			const created = await client.createProfile(draft.newProfileBody());
			profiles = [...profiles, created];
			newCounts = { ...newCounts, [created.id]: 0 };
			editing = null;
			selectProfile(created.id);
			return;
		}
		const updated = await client.updateProfile(profileId, draft.updateBody());
		profiles = profiles.map((profile) => (profile.id === updated.id ? updated : profile));
		editing = null;
	}

	async function deleteProfile(): Promise<void> {
		if (editing === null || editing.profileId === null || profiles === null) return;
		const profileId = editing.profileId;
		await client.deleteProfile(profileId);
		profiles = profiles.filter((profile) => profile.id !== profileId);
		editing = null;
		if (selectedProfileId !== profileId) return;
		selectedProfileId = null;
		listings = null;
		runProgress.disconnect();
		if (profiles.length > 0) selectProfile(profiles[0].id);
	}

	// A config that could not be saved is not shown either, so the app never
	// looks set to something it will not open with.
	async function changeTheme(theme: Theme): Promise<void> {
		const changed = { theme, language: userConfig.language };
		applyTheme(theme);
		try {
			await userConfigFile.save(changed);
		} catch {
			applyTheme(userConfig.theme);
			return;
		}
		userConfig = changed;
	}

	// The panel speaks one language for its whole life, so another one takes
	// a reload, which opens on the same profile and listing again.
	async function changeLanguage(language: Language): Promise<void> {
		const changed = { theme: userConfig.theme, language };
		try {
			await userConfigFile.save(changed);
		} catch {
			return;
		}
		userConfig = changed;
		if (selectedProfileId !== null) keepSelection({ profileId: selectedProfileId, propertyId: selectedPropertyId });
		location.reload();
	}

	async function completeWelcome(config: UserConfig, createProfile: boolean): Promise<void> {
		try {
			await userConfigFile.save(config);
		} catch {
			// Unsaved, the wizard simply shows again on the next launch.
		}
		userConfig = config;
		welcoming = false;
		// The editor saves into the profiles, so it waits until they have loaded.
		if (createProfile && profiles !== null) openNewProfile();
	}

	async function handleRun(): Promise<void> {
		if (selectedProfileId === null) return;
		runError = null;
		try {
			await client.triggerRun(selectedProfileId);
		} catch (err) {
			runError = errorMessage(err);
		}
	}

	// Before the details draw, so a newly selected flat never shows the
	// previous one's photos.
	$effect.pre(() => {
		galleries?.show(
			selectedProfileId === null || selectedPropertyId === null
				? null
				: { profileId: selectedProfileId, propertyId: selectedPropertyId }
		);
	});

	// The places near the open profile's flats follow the profile and its flats.
	$effect(() => {
		const profileId = selectedProfileId;
		const points = (listings ?? []).flatMap((listing) => (listing.point === null ? [] : [listing.point]));
		if (profileId !== null) untrack(() => nearby.show(profileId, points));
	});

	onMount(() => {
		const stopListening = onEngineStopped(() => (engineStopped = true));
		// Taken before anything can fail, so it never outlives the reload it was
		// kept for.
		const kept = takeKeptSelection();
		(async () => {
			try {
				const connection = await sidecarConnection();
				client = new SidecarClient(connection.baseUrl, connection.token);
				galleries = new GalleryStore(client);
				galleries.connect();
				profiles = await client.listProfiles();
			} catch (err) {
				profilesError = errorMessage(err);
				return;
			}
			const opening = profiles.find((profile) => profile.id === kept?.profileId) ?? profiles[0];
			if (opening !== undefined) {
				selectProfile(opening.id);
				if (opening.id === kept?.profileId) selectedPropertyId = kept.propertyId;
			}
			await Promise.all([loadAllNewCounts(profiles ?? []), loadHealth()]);
		})();

		return () => {
			runProgress.disconnect();
			galleries?.disconnect();
			void stopListening.then((unlisten) => unlisten());
		};
	});
</script>

<div class="shell" inert={welcoming || writingFeedback}>
	<header class="topbar">
		<h1 class="topbar__logo"><img src={logo} alt="rentczecher" /></h1>
		<nav class="tabs" aria-label={t.t('Profiles')}>
			{#if profilesError}
				<span class="tabs__status">
					{t.t('Could not load profiles: {message}', { message: profilesError })}
				</span>
			{:else if profiles === null}
				<span class="tabs__status">{t.t('Loading profiles...')}</span>
			{:else}
				{#if profiles.length === 0}
					<span class="tabs__status">{t.t('No profiles yet')}</span>
				{/if}
				{#each profiles as profile (profile.id)}
					{@const selected = profile.id === selectedProfileId}
					<div class="tab" class:tab--selected={selected}>
						<button class="tab__select" onclick={() => selectProfile(profile.id)}>
							{profile.name}
							{#if newCounts[profile.id]}
								<span class="tab__count">{newCounts[profile.id]}</span>
							{/if}
						</button>
						{#if selected}
							<button
								class="tab__edit"
								aria-label={t.t('Edit profile {name}', { name: profile.name })}
								title={t.t('Edit profile {name}', { name: profile.name })}
								onclick={() => openStoredProfile(profile)}
							>
								<svg viewBox="0 0 24 24" aria-hidden="true">
									<path
										fill-rule="evenodd"
										d="M9.91 4.69 L10.36 1.63 L13.64 1.63 L14.09 4.69 L15.68 5.35 L18.17 3.51 L20.49 5.83 L18.65 8.32 L19.31 9.91 L22.37 10.36 L22.37 13.64 L19.31 14.09 L18.65 15.68 L20.49 18.17 L18.17 20.49 L15.68 18.65 L14.09 19.31 L13.64 22.37 L10.36 22.37 L9.91 19.31 L8.32 18.65 L5.83 20.49 L3.51 18.17 L5.35 15.68 L4.69 14.09 L1.63 13.64 L1.63 10.36 L4.69 9.91 L5.35 8.32 L3.51 5.83 L5.83 3.51 L8.32 5.35 Z M15 12a3 3 0 1 0-6 0 3 3 0 1 0 6 0Z"
									/>
								</svg>
							</button>
						{/if}
					</div>
				{/each}
				<button class="tab tab--add" title={t.t('Add profile')} onclick={openNewProfile}>+</button>
			{/if}
		</nav>
		<div class="topbar__end">
			<InboxHeader
				{health}
				runState={runProgress.state}
				lastFinishedAt={runProgress.lastFinishedAt}
				triggerError={runError}
				onrun={handleRun}
			/>
			<span class="topbar__divider" aria-hidden="true"></span>
			<ThemeToggle theme={userConfig.theme} onchange={changeTheme} />
			<LanguageToggle language={userConfig.language} onchange={changeLanguage} />
			<FeedbackButton onclick={() => (writingFeedback = true)} />
		</div>
	</header>

	{#if engineStopped}
		<p class="engine-stopped" role="alert">
			{t.t('rentczecher stopped working. Restart the app to continue.')}
		</p>
	{/if}

	{#if listingsError}
		<p class="shell__status">{t.t('Could not load listings: {message}', { message: listingsError })}</p>
	{:else if profiles !== null && profiles.length === 0}
		<p class="shell__status">{t.t('Create a profile with + to start watching.')}</p>
	{:else if listings === null}
		<p class="shell__status">{t.t('Loading listings...')}</p>
	{:else}
		<!-- Each profile opens fresh: its first listing picked, its own order. -->
		{#key selectedProfileId}
			<Inbox
				{listings}
				preferences={scoring}
				onview={handleViewed}
				onfavourite={handleFavourite}
				onmarkallviewed={handleMarkAllViewed}
				{loadPriceHistory}
				gallery={galleries?.gallery ?? null}
				{nearby}
				bind:selectedId={selectedPropertyId}
			/>
		{/key}
	{/if}
</div>

{#if welcoming}
	<WelcomeWizard theme={userConfig.theme} oncomplete={completeWelcome} />
{/if}

{#if writingFeedback}
	<FeedbackDialog onclose={() => (writingFeedback = false)} />
{/if}

{#if editing !== null}
	<ProfileEditor
		draft={editing.draft}
		stored={editing.profileId !== null}
		searchPlaces={(query, within, kinds) => client.searchPlaces(query, within, kinds)}
		onsave={saveProfile}
		ondelete={deleteProfile}
		oncancel={() => (editing = null)}
	/>
{/if}

<style>
	/* As tall as the window, so the inbox's list and details scroll each on
	their own. */
	.shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
	}

	.engine-stopped {
		margin: var(--space-3) var(--space-4) 0;
		padding: var(--space-2) var(--space-3);
		border-left: 3px solid var(--color-amber);
		background: var(--color-card);
		color: var(--color-bronze);
		font-weight: 600;
	}


	.topbar {
		display: flex;
		align-items: center;
		gap: var(--space-4);
		padding: var(--space-2) var(--space-4) 0;
		border-bottom: 1px solid var(--color-line);
		background: var(--color-card);
	}

	/* The bar pads only its top, seating the tabs on its bottom border, so the
	logo and the end keep as much below them to sit in the middle of the bar. */
	.topbar__logo,
	.topbar__end {
		margin-bottom: var(--space-2);
	}

	.topbar__logo {
		display: flex;
		margin-top: 0;
	}

	.topbar__logo img {
		width: 1.5rem;
		height: 1.5rem;
	}

	.topbar__end {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.topbar__divider {
		width: 1px;
		height: 1.25rem;
		margin: 0 var(--space-1);
		background: var(--color-line);
	}

	/* The tabs stand on the bar's bottom edge, a pixel over its border, so
	the selected one covers the line and joins the inbox below. */
	.tabs {
		display: flex;
		flex: 1;
		align-self: flex-end;
		align-items: flex-end;
		gap: var(--space-1);
		min-width: 0;
		margin-bottom: -1px;
		overflow-x: auto;
	}

	.tab {
		display: flex;
		align-items: center;
		border: 1px solid transparent;
		border-bottom: none;
		border-radius: var(--radius-md) var(--radius-md) 0 0;
		background: none;
		color: var(--color-ink);
		font-size: 0.9375rem;
		white-space: nowrap;
	}

	.tab:hover:not(.tab--selected) {
		background: color-mix(in srgb, var(--color-ground) 60%, var(--color-card));
	}

	.tab--selected {
		background: var(--color-ground);
		border-color: var(--color-line);
		font-weight: 600;
	}

	.tab__select {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		padding: 0.625rem var(--space-4);
		border: none;
		background: none;
		color: inherit;
		font: inherit;
		cursor: pointer;
	}

	.tab--selected .tab__select {
		padding-right: var(--space-2);
	}

	.tab--add {
		padding: 0.5rem 0.875rem;
		font-size: 1.125rem;
		font-weight: 700;
		cursor: pointer;
	}

	.tab__edit {
		display: grid;
		place-items: center;
		width: 1.75rem;
		height: 1.75rem;
		margin-right: var(--space-2);
		padding: 0;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-sm);
		background: var(--color-card);
		color: var(--color-bronze);
		cursor: pointer;
	}

	.tab__edit:hover {
		border-color: var(--color-amber);
		color: var(--color-amber);
	}

	.tab__edit svg {
		width: 1.125rem;
		height: 1.125rem;
		fill: currentColor;
	}

	.tab__count {
		background: var(--color-amber);
		color: var(--color-on-amber);
		border-radius: var(--radius-full);
		font-size: 0.6875rem;
		font-weight: 700;
		padding: 0 var(--space-2);
	}

	.shell__status {
		padding: var(--space-4);
		color: var(--color-bronze);
	}

	.tabs__status {
		font-size: 0.8125rem;
		color: var(--color-bronze);
		padding: var(--space-2) var(--space-3);
		white-space: nowrap;
	}

</style>
