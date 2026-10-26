<script lang="ts">
	import Footer from '$lib/components/Footer.svelte';
	import Header from '$lib/components/Header.svelte';
	import RichText from '$lib/components/RichText.svelte';
	import { MESSAGES, pathsInEveryLanguage } from '$lib/i18n';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const lang = $derived(data.lang);
	const t = $derived(MESSAGES[lang]);
</script>

<svelte:head>
	<title>{t.privacyPolicy.title} · rentczecher</title>
	<meta name="description" content={t.privacyPolicy.intro} />
</svelte:head>

<Header {t} {lang} languagePaths={pathsInEveryLanguage('privacy/')} />
<main class="container">
	<h1 class="section-heading">{t.privacyPolicy.title}</h1>
	<p class="section-intro">{t.privacyPolicy.intro}</p>

	<h2>{t.privacyPolicy.keepsHeading}</h2>
	<ul>
		{#each t.privacyPolicy.keeps as item (item)}
			<li>{item}</li>
		{/each}
	</ul>

	<h2>{t.privacyPolicy.connectionsHeading}</h2>
	<p>{t.privacyPolicy.connectionsIntro}</p>
	<ul>
		{#each t.privacyPolicy.connections as item (item)}
			<li>{item}</li>
		{/each}
	</ul>

	<h2>{t.privacyPolicy.siteHeading}</h2>
	<ul>
		{#each t.privacyPolicy.site as item (item)}
			<li>{item}</li>
		{/each}
	</ul>

	<h2>{t.privacyPolicy.contactHeading}</h2>
	<p><RichText parts={t.privacyPolicy.contact} /></p>
	<p class="muted">{t.privacyPolicy.updated}</p>
</main>
<Footer {t} {lang} />

<style>
	main {
		max-width: calc(68ch + 48px);
		padding-top: 48px;
		padding-bottom: 96px;
		display: flex;
		flex-direction: column;
		gap: 14px;
		line-height: 1.6;
	}

	h2 {
		margin-top: 28px;
		font-size: 24px;
		letter-spacing: -0.01em;
	}

	ul {
		margin: 0;
		padding-left: 22px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
</style>
