<script lang="ts">
	import Footer from '$lib/components/Footer.svelte';
	import Header from '$lib/components/Header.svelte';
	import InstallSteps from '$lib/components/InstallSteps.svelte';
	import RichText from '$lib/components/RichText.svelte';
	import { MESSAGES, pathsInEveryLanguage } from '$lib/i18n';
	import { MACOS_INSTALLER_URL, WINDOWS_INSTALLER_URL } from '$lib/links';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const lang = $derived(data.lang);
	const t = $derived(MESSAGES[lang]);
</script>

<svelte:head>
	<title>{t.install.title} · rentczecher</title>
	<meta name="description" content={t.install.intro} />
</svelte:head>

<Header {t} {lang} languagePaths={pathsInEveryLanguage('install/')} />
<main class="container">
	<h1 class="section-heading">{t.install.title}</h1>
	<p class="section-intro">{t.install.intro}</p>

	<section id="windows" class="card">
		<div class="os-head">
			<h2>{t.install.windowsHeading}</h2>
			<a class="btn btn-amber btn-sm" href={WINDOWS_INSTALLER_URL}>{t.download.button}</a>
		</div>
		<InstallSteps steps={t.install.windowsSteps} />
		<h3>{t.install.smartAppControlHeading}</h3>
		<p><RichText parts={t.install.smartAppControl} /></p>
	</section>

	<section id="macos" class="card">
		<div class="os-head">
			<h2>{t.install.macosHeading}</h2>
			<a class="btn btn-amber btn-sm" href={MACOS_INSTALLER_URL}>{t.download.button}</a>
		</div>
		<InstallSteps steps={t.install.macosSteps} />
		<p class="muted"><RichText parts={t.install.olderMacos} /></p>
		<h3>{t.install.damagedHeading}</h3>
		<p><RichText parts={t.install.damaged} /></p>
		<pre><code>{t.install.damagedCommand}</code></pre>
	</section>

	<h2>{t.install.whyHeading}</h2>
	{#each t.install.why as paragraph (paragraph)}
		<p>{paragraph}</p>
	{/each}
</main>
<Footer {t} {lang} />

<style>
	main {
		max-width: calc(76ch + 48px);
		padding-top: 48px;
		padding-bottom: 96px;
		display: flex;
		flex-direction: column;
		gap: 14px;
		line-height: 1.6;
	}

	section {
		margin-top: 20px;
		padding: 24px;
		display: flex;
		flex-direction: column;
		gap: 16px;
		scroll-margin-top: 96px;
	}

	.os-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		flex-wrap: wrap;
	}

	h2 {
		margin: 0;
		font-size: 24px;
		letter-spacing: -0.01em;
	}

	main > h2 {
		margin-top: 28px;
	}

	h3 {
		margin: 8px 0 0;
		font-size: 18px;
	}

	p {
		margin: 0;
	}

	pre {
		margin: 0;
		padding: 12px 16px;
		overflow-x: auto;
		border-radius: 8px;
		background: var(--code);
		color: var(--code-text);
		font-size: 14px;
	}
</style>
