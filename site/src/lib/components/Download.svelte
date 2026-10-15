<script lang="ts">
	import type { Messages } from '$lib/i18n/messages';
	import { RELEASES_URL, REPO_URL } from '$lib/links';

	let { t, appVersion }: { t: Messages; appVersion: string } = $props();

	const platforms = $derived([
		{ name: 'Windows', detail: t.download.windows },
		{ name: 'macOS', detail: t.download.macos },
		{ name: 'Linux', detail: t.download.linux }
	]);
</script>

<section id="download" class="container">
	<div class="head">
		<h2 class="section-heading">{t.download.heading}</h2>
		<p class="muted">{t.download.version} {appVersion}, {t.download.free}.</p>
		<a href={RELEASES_URL}>{t.download.allReleases}</a>
	</div>
	<div class="grid">
		{#each platforms as platform (platform.name)}
			<div class="card platform">
				<h3>{platform.name}</h3>
				<p class="muted">{platform.detail}</p>
				<a class="btn btn-amber" href={RELEASES_URL}>{t.download.button}</a>
			</div>
		{/each}
	</div>
	<div class="notes muted">
		<p>{t.download.macWarning} <a href="#faq">{t.download.whatToDo}</a></p>
		<p>{t.download.buildYourself} <a href={REPO_URL}>{t.download.readme}</a></p>
	</div>
</section>

<style>
	section {
		padding-top: 80px;
		padding-bottom: 80px;
		display: flex;
		flex-direction: column;
		gap: 28px;
	}

	.head {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
		gap: 20px;
	}

	.platform {
		padding: 24px;
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	.platform h3 {
		font-size: 22px;
	}

	.platform p {
		font-size: 15px;
	}

	.platform .btn {
		align-self: flex-start;
	}

	.notes {
		display: flex;
		flex-direction: column;
		gap: 6px;
		font-size: 15px;
	}
</style>
