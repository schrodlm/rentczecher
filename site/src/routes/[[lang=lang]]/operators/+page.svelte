<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import RichText from '$lib/components/RichText.svelte';
	import { MESSAGES, pathsInEveryLanguage } from '$lib/i18n';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const lang = $derived(data.lang);
	const t = $derived(MESSAGES[lang]);
	const userAgent = $derived(`rentczecher/${data.appVersion} (+https://rentczecher.cz)`);
</script>

<svelte:head>
	<title>{t.operators.title} · rentczecher</title>
	<meta name="description" content={t.operators.intro} />
</svelte:head>

<Header {t} {lang} languagePaths={pathsInEveryLanguage('operators/')} />
<main class="container">
	<h1 class="section-heading">{t.operators.title}</h1>
	<p class="section-intro">{t.operators.intro}</p>

	<h2>{t.operators.whatHeading}</h2>
	<ul>
		{#each t.operators.whatItIs as item (item)}
			<li>{item}</li>
		{/each}
	</ul>

	<h2>{t.operators.howHeading}</h2>
	<p>{t.operators.userAgentIntro}</p>
	<pre class="mono">{userAgent}</pre>
	<ul>
		{#each t.operators.howItReads as item (item)}
			<li>{item}</li>
		{/each}
	</ul>

	<h2>{t.operators.contactHeading}</h2>
	<p><RichText parts={t.operators.contact} /></p>
	<p class="muted">{t.operators.notAffiliated}</p>
</main>

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

	pre {
		margin: 0;
		background: var(--code);
		color: var(--code-text);
		border-radius: 8px;
		padding: 14px 16px;
		font-size: 14px;
		overflow-x: auto;
	}
</style>
