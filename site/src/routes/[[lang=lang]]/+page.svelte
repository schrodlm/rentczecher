<script lang="ts">
	import Devlog from '$lib/components/Devlog.svelte';
	import Download from '$lib/components/Download.svelte';
	import Faq from '$lib/components/Faq.svelte';
	import Features from '$lib/components/Features.svelte';
	import Header from '$lib/components/Header.svelte';
	import Hero from '$lib/components/Hero.svelte';
	import OpenSource from '$lib/components/OpenSource.svelte';
	import Portals from '$lib/components/Portals.svelte';
	import PrivacyBand from '$lib/components/PrivacyBand.svelte';
	import Roadmap from '$lib/components/Roadmap.svelte';
	import { LANGUAGES, MESSAGES, homePath, pathsInEveryLanguage } from '$lib/i18n';
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
	<meta property="og:image" content="{SITE_ORIGIN}/logo.png" />
</svelte:head>

<Header {t} {lang} languagePaths={pathsInEveryLanguage('')} />
<main id="top">
	<Hero {t} appVersion={data.appVersion} />
	<Portals {t} />
	<Features {t} />
	<PrivacyBand {t} />
	<OpenSource {t} appVersion={data.appVersion} />
	<Download {t} appVersion={data.appVersion} />
	<Roadmap {t} />
	<Devlog {t} {lang} entries={data.latestDevlog} />
	<Faq {t} />
</main>
