<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import { formatDate } from '$lib/format';
	import { DEVLOG_LANGUAGE, MESSAGES } from '$lib/i18n';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const t = MESSAGES[DEVLOG_LANGUAGE];
</script>

<svelte:head>
	<title>{data.post.title} · rentczecher</title>
	<meta name="description" content={data.post.summary} />
	<meta property="og:title" content={data.post.title} />
	<meta property="og:description" content={data.post.summary} />
</svelte:head>

<Header {t} lang={DEVLOG_LANGUAGE} />
<main class="container">
	<a class="back" href="/devlog/">← {t.devlog.allPosts}</a>
	<h1>{data.post.title}</h1>
	<p class="meta">
		{formatDate(data.post.date, DEVLOG_LANGUAGE)} · {t.devlog.minutesToRead(data.minutesToRead)}
	</p>
	<!-- The HTML is rendered at build time from the repository's own Markdown files. -->
	<article>{@html data.html}</article>
</main>

<style>
	main {
		max-width: calc(68ch + 48px);
		padding-top: 40px;
		padding-bottom: 96px;
	}

	.back {
		font-weight: 700;
		font-size: 15px;
	}

	h1 {
		margin-top: 24px;
		font-size: clamp(32px, 4.5vw, 44px);
		line-height: 1.15;
		letter-spacing: -0.02em;
	}

	.meta {
		margin-top: 12px;
		font-size: 14px;
		color: var(--muted);
	}

	article {
		margin-top: 32px;
		line-height: 1.7;
	}

	article :global(h2) {
		margin: 40px 0 12px;
		font-size: 24px;
		letter-spacing: -0.01em;
	}

	article :global(p),
	article :global(ul),
	article :global(ol) {
		margin: 0 0 18px;
	}

	article :global(li) {
		margin-bottom: 8px;
	}

	article :global(code) {
		font-family: ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, Consolas, monospace;
		font-size: 0.9em;
	}
</style>
