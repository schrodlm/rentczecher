<script lang="ts">
	import type { Messages, RoadmapColumn } from '$lib/i18n/messages';
	import { ISSUES_URL } from '$lib/links';

	let { t }: { t: Messages } = $props();

	type Stage = 'in-progress' | 'next' | 'later';

	const columns: Array<{ stage: Stage; column: RoadmapColumn }> = $derived([
		{ stage: 'in-progress', column: t.roadmap.inProgress },
		{ stage: 'next', column: t.roadmap.next },
		{ stage: 'later', column: t.roadmap.later }
	]);
</script>

<section id="roadmap" class="band-surface">
	<div class="container inner">
		<div class="head">
			<div class="head-text">
				<h2 class="section-heading">{t.roadmap.heading}</h2>
				<p class="section-intro">{t.roadmap.intro}</p>
			</div>
			<a class="btn btn-line" href={ISSUES_URL}>{t.roadmap.suggest}</a>
		</div>
		<div class="grid">
			{#each columns as { stage, column } (stage)}
				<div class="column">
					<span class="chip chip-{stage}">{column.label}</span>
					<ul>
						{#each column.items as item (item.title)}
							<li class="item item-{stage}">
								<strong>{item.title}</strong>
								<span class="muted">{item.body}</span>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>
	</div>
</section>

<style>
	.inner {
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

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
		gap: 20px;
	}

	.column {
		display: flex;
		flex-direction: column;
		gap: 14px;
	}

	.chip-in-progress {
		background: var(--amber);
		color: var(--on-amber);
	}

	.chip-next {
		background: var(--olive);
		color: var(--on-olive);
	}

	.chip-later {
		border: 1px solid var(--line-strong);
		color: var(--muted);
	}

	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.item {
		background: var(--bg);
		border: 1px solid var(--line);
		border-radius: 10px;
		padding: 16px 18px;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.item-later {
		border-style: dashed;
		border-color: var(--line-strong);
	}

	.item span {
		font-size: 15px;
	}
</style>
