<script lang="ts">
	import Icon from './Icon.svelte';
	import type { Messages } from '$lib/i18n/messages';
	import {
		CLONE_COMMAND,
		ISSUES_URL,
		NEW_ISSUE_URL,
		RELEASES_URL,
		REPO_LABEL,
		REPO_URL,
		SUPPORT_URL
	} from '$lib/links';

	let { t, appVersion }: { t: Messages; appVersion: string } = $props();
</script>

<section class="container">
	<div class="pitch">
		<span class="chip chip-outline">{t.openSource.chip}</span>
		<h2 class="section-heading">{t.openSource.heading}</h2>
		<p class="section-intro">{t.openSource.body}</p>
		<div class="buttons">
			<a class="btn btn-amber" href={REPO_URL}>
				<Icon name="star" />
				{t.openSource.star}
			</a>
			<a class="btn btn-line" href={NEW_ISSUE_URL}>
				<Icon name="alert" />
				{t.openSource.reportBug}
			</a>
		</div>
	</div>

	<div class="card repo">
		<a class="repo-name" href={REPO_URL}>
			<Icon name="book" />
			<span class="mono">{REPO_LABEL}</span>
		</a>
		<div class="repo-body">
			<p class="muted">{t.openSource.repoDescription}</p>
			<ul class="facts">
				<li>{t.openSource.licence} GPL-3.0</li>
				<li><a href={RELEASES_URL}>v{appVersion}</a></li>
				<li><a href={ISSUES_URL}>Issues</a></li>
			</ul>
			<div class="clone mono"><span class="prompt">$</span>{CLONE_COMMAND}</div>
		</div>
	</div>

	<div class="card author">
		<img src="/logo.png" alt="" width="56" height="56" />
		<div class="author-text">
			<h3>{t.openSource.authorHeading}</h3>
			<p class="muted">{t.openSource.authorBody}</p>
		</div>
		<a class="btn btn-line" href={SUPPORT_URL}>
			<Icon name="heart" />
			{t.openSource.support}
		</a>
	</div>
</section>

<style>
	section {
		padding-top: 88px;
		padding-bottom: 40px;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
		gap: 40px 56px;
		align-items: center;
	}

	.pitch {
		display: flex;
		flex-direction: column;
		gap: 18px;
	}

	.chip-outline {
		border: 1px solid var(--line-strong);
		color: var(--link);
	}

	.buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
	}

	.repo {
		overflow: hidden;
		box-shadow: 0 10px 30px var(--shadow);
	}

	.repo-name {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 18px 20px;
		border-bottom: 1px solid var(--line);
		color: var(--text);
		text-decoration: none;
		font-weight: 700;
		font-size: 15px;
	}

	.repo-body {
		padding: 18px 20px;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.repo-body p {
		line-height: 1.5;
	}

	.facts {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 8px 20px;
		font-size: 14px;
		color: var(--muted);
	}

	.clone {
		background: var(--code);
		color: var(--code-text);
		border-radius: 8px;
		padding: 14px 16px;
		font-size: 14px;
		overflow-x: auto;
		white-space: nowrap;
	}

	.prompt {
		color: var(--code-dim);
		margin-right: 1ch;
	}

	.author {
		grid-column: 1 / -1;
		padding: 28px;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 20px 32px;
	}

	.author-text {
		flex: 999 1 420px;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.author-text h3 {
		font-size: 22px;
	}

	.author-text p {
		line-height: 1.6;
		max-width: 60ch;
	}
</style>
