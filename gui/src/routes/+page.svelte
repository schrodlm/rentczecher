<script lang="ts">
	import { onMount } from 'svelte';
	import { env } from '$env/dynamic/public';
	import { SidecarClient } from '$lib/api/client';
	import type { components } from '$lib/api/types.gen';
	import { getTranslatorContext } from '$lib/i18n/context';

	type Profile = components['schemas']['ProfileModel'];

	const t = getTranslatorContext();

	let profiles = $state<Profile[] | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		const client = new SidecarClient(env.PUBLIC_SIDECAR_BASE_URL ?? '', env.PUBLIC_SIDECAR_TOKEN ?? '');
		try {
			profiles = await client.listProfiles();
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		}
	});
</script>

<main>
	<h1>rentczecher</h1>
	<h2>{t.t('Profiles')}</h2>

	{#if error}
		<p>{t.t('Could not load profiles')}: {error}</p>
	{:else if profiles === null}
		<p>{t.t('Loading...')}</p>
	{:else}
		<p>{t.tn('{count} profile', '{count} profiles', profiles.length)}</p>
		<ul>
			{#each profiles as profile (profile.id)}
				<li>
					{t.t('{name} ({status})', {
						name: profile.name,
						status: profile.enabled ? t.t('enabled') : t.t('disabled')
					})}
				</li>
			{/each}
		</ul>
	{/if}
</main>
