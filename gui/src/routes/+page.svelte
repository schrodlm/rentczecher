<script lang="ts">
	import { onMount } from 'svelte';
	import { env } from '$env/dynamic/public';
	import logo from '$lib/assets/logo.svg';
	import { SidecarClient } from '$lib/api/client';
	import type { components } from '$lib/api/types.gen';
	import { getTranslatorContext } from '$lib/i18n/context';

	type ProfileModel = components['schemas']['ProfileModel'];

	const t = getTranslatorContext();
	const client = new SidecarClient(
		env.PUBLIC_SIDECAR_BASE_URL ?? '',
		env.PUBLIC_SIDECAR_TOKEN ?? ''
	);

	let profiles = $state<ProfileModel[] | null>(null);
	let profilesError = $state<string | null>(null);
	let selectedProfileId = $state<string | null>(null);

	onMount(async () => {
		try {
			profiles = await client.listProfiles();
		} catch (err) {
			profilesError = err instanceof Error ? err.message : String(err);
			return;
		}
		if (profiles.length > 0) {
			selectedProfileId = profiles[0].id;
		}
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
							onclick={() => (selectedProfileId = profile.id)}
						>
							{profile.name}
						</button>
					{/each}
					<button class="tab tab--add" title={t.t('Add profile')}>+</button>
				{/if}
			</nav>
			<div class="topbar__actions">
				<span class="topbar__lastrun">{t.t('Last scan: {time}', { time: 'dnes 10:32' })}</span>
				<button class="topbar__run">{t.t('Run scan')}</button>
			</div>
		</header>

		<main class="feed">
			<section>
				<h3 class="feed__heading">{t.t('New')}</h3>
				<article class="card card--new">
					<span class="card__badge">{t.t('New')}</span>
					<div class="card__title">Byt 2+kk, 54 m²</div>
					<div class="card__meta">Praha 7, Holešovice</div>
					<div class="card__price">25 000 Kč <span class="card__drop">sleva z 27 000 Kč</span></div>
				</article>
				<article class="card card--new">
					<span class="card__badge">{t.t('New')}</span>
					<div class="card__title">Byt 3+1, 78 m²</div>
					<div class="card__meta">Praha 7, Letná</div>
					<div class="card__price">32 500 Kč</div>
				</article>
			</section>
			<section>
				<h3 class="feed__heading">{t.t('Viewed')}</h3>
				<article class="card card--viewed">
					<div class="card__title">Byt 1+kk, 32 m²</div>
					<div class="card__meta">Praha 7, Bubeneč</div>
					<div class="card__price">19 900 Kč</div>
				</article>
			</section>
		</main>
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

	.tabs__status {
		font-size: 0.8125rem;
		color: var(--color-bronze);
		padding: var(--space-2) var(--space-3);
		white-space: nowrap;
	}

	.topbar__actions {
		display: flex;
		align-items: center;
		gap: var(--space-3);
	}

	.topbar__lastrun {
		font-size: 0.8125rem;
		color: var(--color-bronze);
		white-space: nowrap;
	}

	.topbar__run {
		background: var(--color-amber);
		color: var(--color-on-amber);
		border: none;
		border-radius: var(--radius-md);
		padding: var(--space-2) var(--space-4);
		font-weight: 600;
		cursor: pointer;
		margin-bottom: var(--space-2);
	}

	.topbar__run:hover {
		background: var(--color-amber-bright);
	}

	.feed {
		padding: var(--space-4);
		display: flex;
		flex-direction: column;
		gap: var(--space-6);
		overflow-y: auto;
	}

	.feed__heading {
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--color-bronze);
		margin: 0 0 var(--space-2);
	}

	.card {
		background: var(--color-card);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		padding: var(--space-3) var(--space-4);
		margin-bottom: var(--space-3);
	}

	.card--new {
		border-color: var(--color-amber);
		position: relative;
	}

	.card__badge {
		position: absolute;
		top: var(--space-3);
		right: var(--space-3);
		background: var(--color-amber);
		color: var(--color-on-amber);
		border-radius: var(--radius-full);
		font-size: 0.625rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: 0 var(--space-2);
	}

	.card__drop {
		color: var(--color-olive);
		font-size: 0.8125rem;
		font-weight: 600;
		margin-left: var(--space-2);
	}

	.card--viewed {
		opacity: 0.6;
	}

	.card__title {
		font-weight: 600;
	}

	.card__meta {
		font-size: 0.8125rem;
		color: var(--color-bronze);
	}

	.card__price {
		margin-top: var(--space-1);
		font-weight: 600;
	}
</style>
