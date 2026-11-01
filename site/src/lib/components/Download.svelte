<script lang="ts">
	import { homePath, type Language } from '$lib/i18n';
	import type { Messages } from '$lib/i18n/messages';
	import {
		LINUX_APPIMAGE_URL,
		LINUX_DEB_URL,
		MACOS_INSTALLER_URL,
		RELEASES_URL,
		REPO_URL,
		WINDOWS_INSTALLER_URL
	} from '$lib/links';

	let { t, lang, appVersion }: { t: Messages; lang: Language; appVersion: string } = $props();

	const installPath = $derived(`${homePath(lang)}install/`);

	const platforms = $derived([
		{
			name: 'Windows',
			detail: t.download.windows,
			downloads: [{ label: t.download.button, href: WINDOWS_INSTALLER_URL }],
			installSteps: `${installPath}#windows`
		},
		{
			name: 'macOS',
			detail: t.download.macos,
			downloads: [{ label: t.download.button, href: MACOS_INSTALLER_URL }],
			installSteps: `${installPath}#macos`
		},
		{
			name: 'Linux',
			detail: t.download.linux,
			downloads: [
				{ label: 'AppImage', href: LINUX_APPIMAGE_URL },
				{ label: '.deb', href: LINUX_DEB_URL }
			],
			installSteps: null
		}
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
				<div class="downloads">
					{#each platform.downloads as download (download.href)}
						<a class="btn btn-amber" href={download.href}>{download.label}</a>
					{/each}
				</div>
				{#if platform.installSteps !== null}
					<a class="install-steps" href={platform.installSteps}>{t.download.installSteps}</a>
				{/if}
			</div>
		{/each}
	</div>
	<p class="warning">
		{t.download.firstLaunchWarning} <a href={installPath}>{t.download.installSteps}</a>
	</p>
	<p class="notes muted">{t.download.buildYourself} <a href={REPO_URL}>{t.download.readme}</a></p>
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

	.downloads {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}

	.platform .btn {
		align-self: flex-start;
	}

	.install-steps {
		font-size: 15px;
	}

	.warning {
		margin: 0;
		padding: 14px 18px;
		border: 1px solid var(--amber);
		border-radius: 10px;
		background: color-mix(in srgb, var(--amber) 10%, var(--surface));
		font-size: 15px;
	}

	.notes {
		margin: 0;
		font-size: 15px;
	}
</style>
