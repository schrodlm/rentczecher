<script lang="ts">
	import { onMount } from 'svelte';
	import { env } from '$env/dynamic/public';
	import logo from '$lib/assets/logo.svg';
	import { SidecarClient } from '$lib/api/client';
	import type { ListingModel, PortalHealthModel, ProfileModel } from '$lib/api/client';
	import { errorMessage } from '$lib/errors';
	import InboxHeader from '$lib/components/InboxHeader.svelte';
	import ListingFeed from '$lib/components/ListingFeed.svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { RunProgressStore } from '$lib/stores/run-progress.svelte';

	const t = getTranslatorContext();
	const client = new SidecarClient(
		env.PUBLIC_SIDECAR_BASE_URL ?? '',
		env.PUBLIC_SIDECAR_TOKEN ?? ''
	);

	const runProgress = new RunProgressStore();

	let profiles = $state<ProfileModel[] | null>(null);
	let profilesError = $state<string | null>(null);
	let selectedProfileId = $state<string | null>(null);
	let health = $state<PortalHealthModel[]>([]);
	let runError = $state<string | null>(null);
	let listings = $state<ListingModel[] | null>(null);
	let listingsError = $state<string | null>(null);
	let newCounts = $state<Record<string, number>>({});

	const newListings = $derived(
		[...(listings ?? [])]
			.filter((l) => l.viewed_at === null)
			.sort((a, b) => b.first_seen_at.localeCompare(a.first_seen_at))
	);
	const viewedListings = $derived(
		[...(listings ?? [])]
			.filter((l) => l.viewed_at !== null)
			.sort((a, b) => (b.viewed_at ?? '').localeCompare(a.viewed_at ?? ''))
	);

	async function loadListings(profileId: string): Promise<void> {
		listingsError = null;
		try {
			const fetched = await client.listListings(profileId, 'all');
			// A slow response for a tab the user already left must not
			// overwrite the tab they are on.
			if (profileId !== selectedProfileId) return;
			listings = fetched;
			newCounts = {
				...newCounts,
				[profileId]: fetched.filter((l) => l.viewed_at === null).length
			};
		} catch (err) {
			if (profileId !== selectedProfileId) return;
			listingsError = errorMessage(err);
		}
	}

	async function loadAllNewCounts(profileList: ProfileModel[]): Promise<void> {
		const others = profileList.filter((profile) => profile.id !== selectedProfileId);
		const counts = await Promise.all(
			others.map(async (profile) => {
				try {
					const newOnes = await client.listListings(profile.id, 'new');
					return [profile.id, newOnes.length] as const;
				} catch {
					return [profile.id, 0] as const;
				}
			})
		);
		newCounts = { ...newCounts, ...Object.fromEntries(counts) };
	}

	async function handleViewed(listingId: string): Promise<void> {
		if (selectedProfileId === null) return;
		try {
			await client.markViewed(selectedProfileId, listingId);
		} catch {
			// A failed PATCH is not retried, the listing stays new until the
			// next reload.
			return;
		}
		const marked = listings?.find((l) => l.id === listingId);
		if (marked && marked.viewed_at === null) {
			marked.viewed_at = new Date().toISOString();
			newCounts = {
				...newCounts,
				[selectedProfileId]: Math.max(0, (newCounts[selectedProfileId] ?? 1) - 1)
			};
		}
	}

	async function handleMarkAllViewed(): Promise<void> {
		if (selectedProfileId === null) return;
		const profileId = selectedProfileId;
		await Promise.all(newListings.map((l) => client.markViewed(profileId, l.id).catch(() => {})));
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
		selectedProfileId = profileId;
		listings = null;
		void loadListings(profileId);
		runProgress.connect(client.eventsUrl(), profileId, () => {
			void loadListings(profileId);
			void loadHealth();
		});
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

	onMount(() => {
		(async () => {
			try {
				profiles = await client.listProfiles();
			} catch (err) {
				profilesError = errorMessage(err);
				return;
			}
			if (profiles.length > 0) {
				selectProfile(profiles[0].id);
				await loadAllNewCounts(profiles);
			}
			await loadHealth();
		})();

		return () => runProgress.disconnect();
	});
</script>

<div class="shell">
	<aside class="sidebar">
		<h1 class="sidebar__brand">
			<img class="sidebar__logo" src={logo} alt="" />
			rentczecher
		</h1>
		<button class="sidebar__settings">{t.t('Settings')}</button>
	</aside>

	<div class="shell__main">
		<header class="topbar">
			<nav class="tabs" aria-label={t.t('Profiles')}>
				{#if profilesError}
					<span class="tabs__status">
						{t.t('Could not load profiles: {message}', { message: profilesError })}
					</span>
				{:else if profiles === null}
					<span class="tabs__status">{t.t('Loading profiles...')}</span>
				{:else if profiles.length === 0}
					<span class="tabs__status">{t.t('No profiles yet')}</span>
				{:else}
					{#each profiles as profile (profile.id)}
						<button
							class="tab"
							class:tab--selected={profile.id === selectedProfileId}
							onclick={() => selectProfile(profile.id)}
						>
							{profile.name}
							{#if newCounts[profile.id]}
								<span class="tab__count">{newCounts[profile.id]}</span>
							{/if}
						</button>
					{/each}
					<button class="tab tab--add" title={t.t('Add profile')}>+</button>
				{/if}
			</nav>
			<InboxHeader
				{health}
				runState={runProgress.state}
				lastFinishedAt={runProgress.lastFinishedAt}
				triggerError={runError}
				onrun={handleRun}
			/>
		</header>

		{#if listingsError}
			<p class="shell__status">{t.t('Could not load listings: {message}', { message: listingsError })}</p>
		{:else if listings === null}
			<p class="shell__status">{t.t('Loading listings...')}</p>
		{:else}
			<ListingFeed {newListings} {viewedListings} onviewed={handleViewed} onmarkallviewed={handleMarkAllViewed} />
		{/if}
	</div>
</div>

<style>
	.shell {
		display: grid;
		grid-template-columns: 11rem 1fr;
		min-height: 100vh;
	}

	.sidebar {
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		background: var(--color-card);
		border-right: 1px solid var(--color-line);
		padding: var(--space-4);
	}

	.sidebar__brand {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		font-size: 1.125rem;
		margin: 0;
	}

	.sidebar__logo {
		width: 1.5rem;
		height: 1.5rem;
	}

	.sidebar__settings {
		background: var(--color-ground);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		color: inherit;
		text-align: center;
		padding: var(--space-2) var(--space-4);
		cursor: pointer;
		font-size: 0.875rem;
	}

	.sidebar__settings:hover {
		background: var(--color-line);
	}

	.shell__main {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.topbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-4);
		padding: var(--space-2) var(--space-4) 0;
		border-bottom: 1px solid var(--color-line);
		background: var(--color-card);
	}

	.tabs {
		display: flex;
		align-items: flex-end;
		gap: var(--space-1);
		min-width: 0;
		overflow-x: auto;
	}

	.tab {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		background: none;
		border: 1px solid transparent;
		border-bottom: none;
		border-radius: var(--radius-md) var(--radius-md) 0 0;
		padding: var(--space-2) var(--space-3);
		color: var(--color-ink);
		font-size: 0.875rem;
		white-space: nowrap;
		cursor: pointer;
	}

	.tab--selected {
		background: var(--color-ground);
		border-color: var(--color-line);
		font-weight: 600;
	}

	.tab--add {
		font-weight: 700;
		padding: var(--space-2);
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
