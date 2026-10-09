<script lang="ts">
	import '$lib/styles/preferences.css';
	import type { Snippet } from 'svelte';
	import type { Preference } from './preferences';

	/* One preference: its share of the score while it counts, its preferred
	value and the rule it scores by. It counts once its preferred value is set. */
	let {
		preference,
		title,
		share,
		rule,
		children
	}: {
		preference: Preference;
		title: string;
		share: number | null;
		rule: string;
		children: Snippet;
	} = $props();
</script>

<div class="preference-card preference-{preference}" class:preference-card--off={share === null}>
	<div class="preference-card__head">
		<strong class="preference-card__title">{title}</strong>
		{#if share !== null}
			<span class="preference-card__share">{share} %</span>
		{/if}
	</div>
	{@render children()}
	<p class="preference-card__rule">{rule}</p>
</div>

<style>
	.preference-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-3) var(--space-3) var(--space-3) var(--space-4);
		border: 1px solid var(--color-line);
		border-left: 4px solid var(--preference);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.preference-card--off {
		border-left-color: var(--color-line);
		background: var(--color-ground);
	}

	.preference-card__head {
		display: flex;
		align-items: center;
		gap: var(--space-2);
	}

	.preference-card__title {
		flex: 1;
	}

	.preference-card--off .preference-card__title {
		color: var(--color-bronze);
	}

	.preference-card__share {
		padding: 0 var(--space-2);
		border-radius: var(--radius-full);
		background: var(--preference);
		color: var(--preference-text);
		font-size: 0.75rem;
		font-weight: 700;
	}

	.preference-card__rule {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}
</style>
