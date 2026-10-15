<script lang="ts">
	import Icon from './Icon.svelte';
	import ThemeToggle from './ThemeToggle.svelte';
	import { LANGUAGES, homePath, type Language } from '$lib/i18n';
	import type { Messages } from '$lib/i18n/messages';
	import { REPO_URL } from '$lib/links';

	let { t, lang }: { t: Messages; lang: Language } = $props();
</script>

<a class="topbar" href={REPO_URL}>{t.topbar}</a>

<header class="container">
	<a class="brand" href={homePath(lang)}>
		<img src="/logo.png" alt="" width="36" height="36" />
		rentczecher
	</a>
	<nav aria-label={t.nav.label}>
		<a href="{homePath(lang)}#features">{t.nav.features}</a>
		<a href="{homePath(lang)}#roadmap">{t.nav.roadmap}</a>
		<a href="{homePath(lang)}#devlog">{t.nav.devlog}</a>
		<a href="{homePath(lang)}#faq">{t.nav.faq}</a>
	</nav>
	<div class="controls">
		<a class="btn btn-line btn-sm" href={REPO_URL}>
			<Icon name="branch" size={18} />
			GitHub
		</a>
		<div class="languages" role="group" aria-label={t.languageLabel}>
			{#each LANGUAGES as option (option)}
				<!-- A full load, so the server sets the html lang attribute for the new language. -->
				<a
					href={homePath(option)}
					data-sveltekit-reload
					hreflang={option}
					lang={option}
					aria-current={option === lang ? 'page' : undefined}>{option.toUpperCase()}</a
				>
			{/each}
		</div>
		<ThemeToggle {t} />
	</div>
</header>

<style>
	.topbar {
		display: block;
		background: var(--band);
		color: var(--band-text);
		text-decoration: none;
		font-size: 14px;
		text-align: center;
		padding: 10px 24px;
	}

	.topbar:hover {
		color: var(--band-text);
		text-decoration: underline;
	}

	header {
		padding-top: 18px;
		padding-bottom: 18px;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 14px 24px;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 10px;
		color: var(--text);
		text-decoration: none;
		font-weight: 800;
		font-size: 20px;
		letter-spacing: -0.01em;
		margin-right: auto;
	}

	nav {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px 22px;
		font-size: 15px;
	}

	nav a {
		color: var(--text);
		text-decoration: none;
	}

	nav a:hover {
		color: var(--link);
	}

	.controls {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.languages {
		display: inline-flex;
		border: 1px solid var(--line-strong);
		border-radius: 999px;
		padding: 3px;
		gap: 2px;
	}

	.languages a {
		min-width: 44px;
		height: 36px;
		border-radius: 999px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--text);
		text-decoration: none;
		font-size: 14px;
		font-weight: 700;
	}

	.languages a[aria-current='page'] {
		background: var(--text);
		color: var(--bg);
	}
</style>
