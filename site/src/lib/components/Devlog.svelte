<script lang="ts">
	import DevlogCard from './DevlogCard.svelte';
	import { DEVLOG_LANGUAGE, type Language } from '$lib/i18n';
	import type { Messages } from '$lib/i18n/messages';
	import type { DevlogEntry } from '$lib/server/devlog';

	let { t, lang, entries }: { t: Messages; lang: Language; entries: DevlogEntry[] } = $props();
</script>

<section id="devlog" class="container">
	<div class="head">
		<div class="head-text">
			<h2 class="section-heading">{t.devlog.heading}</h2>
			<p class="section-intro">{t.devlog.intro}</p>
			{#if lang !== DEVLOG_LANGUAGE}
				<p class="muted">{t.devlog.writtenInEnglish}</p>
			{/if}
		</div>
		<a class="all" href="/devlog/">{t.devlog.allPosts} →</a>
	</div>
	<div class="grid">
		{#each entries as entry (entry.post.slug)}
			<DevlogCard {t} {lang} {entry} />
		{/each}
	</div>
</section>

<style>
	section {
		padding-top: 80px;
		padding-bottom: 80px;
		display: flex;
		flex-direction: column;
		gap: 32px;
	}

	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: 16px 32px;
	}

	.head-text {
		display: flex;
		flex-direction: column;
		gap: 12px;
		max-width: 38em;
		margin-right: auto;
	}

	.all {
		font-weight: 700;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
		gap: 20px;
	}
</style>
