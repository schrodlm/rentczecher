<script lang="ts">
	import { LANGUAGES, MESSAGES, homePath } from '$lib/i18n';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const SITE_ORIGIN = 'https://rentczecher.cz';

	const lang = $derived(data.lang);
	const t = $derived(MESSAGES[lang]);
</script>

<svelte:head>
	<title>{t.meta.title}</title>
	<meta name="description" content={t.meta.description} />
	<link rel="canonical" href="{SITE_ORIGIN}{homePath(lang)}" />
	{#each LANGUAGES as alternate (alternate)}
		<link rel="alternate" hreflang={alternate} href="{SITE_ORIGIN}{homePath(alternate)}" />
	{/each}
	<meta property="og:title" content={t.meta.title} />
	<meta property="og:description" content={t.meta.description} />
</svelte:head>
