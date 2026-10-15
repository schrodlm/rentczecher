<script lang="ts">
	import { formatDate } from '$lib/format';
	import type { Language } from '$lib/i18n';
	import type { Messages } from '$lib/i18n/messages';
	import type { DevlogEntry } from '$lib/server/devlog';

	let { t, lang, entry }: { t: Messages; lang: Language; entry: DevlogEntry } = $props();
</script>

<a class="card" href="/devlog/{entry.post.slug}/">
	<span class="meta"
		>{formatDate(entry.post.date, lang)} · {t.devlog.minutesToRead(entry.minutesToRead)}</span
	>
	<strong>{entry.post.title}</strong>
	<span class="muted summary">{entry.post.summary}</span>
	<span class="read">{t.devlog.read} →</span>
</a>

<style>
	a {
		padding: 24px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		color: var(--text);
		text-decoration: none;
	}

	.meta {
		font-size: 13px;
		color: var(--muted);
	}

	strong {
		font-size: 20px;
		line-height: 1.3;
	}

	.summary {
		line-height: 1.5;
	}

	.read {
		color: var(--link);
		font-weight: 700;
		margin-top: auto;
	}
</style>
