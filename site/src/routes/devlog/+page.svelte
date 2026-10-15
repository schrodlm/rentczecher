<script lang="ts">
	import DevlogCard from '$lib/components/DevlogCard.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import Header from '$lib/components/Header.svelte';
	import { DEVLOG_LANGUAGE, MESSAGES, pathsInEveryLanguage } from '$lib/i18n';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const t = MESSAGES[DEVLOG_LANGUAGE];
</script>

<svelte:head>
	<title>{t.devlog.heading} · rentczecher</title>
	<meta name="description" content={t.devlog.intro} />
</svelte:head>

<Header {t} lang={DEVLOG_LANGUAGE} languagePaths={pathsInEveryLanguage('')} />
<main class="container">
	<h1 class="section-heading">{t.devlog.heading}</h1>
	<p class="section-intro">{t.devlog.intro}</p>
	<div class="posts">
		{#each data.entries as entry (entry.post.slug)}
			<DevlogCard {t} lang={DEVLOG_LANGUAGE} {entry} />
		{/each}
	</div>
</main>
<Footer {t} lang={DEVLOG_LANGUAGE} />

<style>
	main {
		padding-top: 48px;
		padding-bottom: 96px;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.posts {
		margin-top: 16px;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
		gap: 20px;
	}
</style>
