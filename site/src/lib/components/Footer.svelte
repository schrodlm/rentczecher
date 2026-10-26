<script lang="ts">
	import { homePath, type Language } from '$lib/i18n';
	import type { Messages } from '$lib/i18n/messages';
	import { REPO_URL, SUPPORT_URL } from '$lib/links';

	let { t, lang }: { t: Messages; lang: Language } = $props();
</script>

<footer>
	<div class="container inner">
		<span class="credit">
			<img src="/logo.png" alt="" width="24" height="24" />
			{t.footer.credit}
		</span>
		<nav aria-label={t.footer.label}>
			<a class="github" href={REPO_URL}>GitHub</a>
			<a href="/devlog/">{t.nav.devlog}</a>
			<a href="{homePath(lang)}operators/">{t.footer.operators}</a>
			<a href="{homePath(lang)}privacy/">{t.footer.privacyPolicy}</a>
			<a href={SUPPORT_URL}>{t.footer.support}</a>
		</nav>
	</div>
</footer>

<style>
	footer {
		border-top: 1px solid var(--line);
	}

	.inner {
		padding-top: 32px;
		padding-bottom: 48px;
		display: flex;
		flex-wrap: wrap;
		gap: 16px 28px;
		align-items: center;
		font-size: 14px;
		color: var(--muted);
	}

	.credit {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-right: auto;
	}

	nav {
		display: flex;
		flex-wrap: wrap;
		gap: 8px 28px;
	}

	.github {
		font-weight: 700;
	}
</style>
