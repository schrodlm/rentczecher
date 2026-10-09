<script lang="ts">
	import type { Snippet } from 'svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { IMPORTANCES, type Importance } from './wishes';

	/* One wish: how much it matters, the setting it scores against and the rule
	it scores by. Until the setting is chosen the wish can only be off. */
	let {
		title,
		importance = $bindable(),
		ready,
		rule,
		children
	}: { title: string; importance: Importance; ready: boolean; rule: string; children: Snippet } = $props();

	const t = getTranslatorContext();

	function importanceName(level: Importance): string {
		if (level === 0) return t.t('Off');
		if (level === 1) return t.t('Low');
		if (level === 2) return t.t('Medium');
		if (level === 3) return t.t('High');
		return t.t('Top');
	}
</script>

<div class="wish-card" class:wish-card--on={importance > 0}>
	<div class="wish-card__head">
		<strong class="wish-card__title">{title}</strong>
		<div class="wish-card__levels" role="radiogroup" aria-label={t.t('How much {wish} matters', { wish: title })}>
			{#each IMPORTANCES as level (level)}
				<button
					type="button"
					role="radio"
					class="wish-card__level"
					class:wish-card__level--on={importance === level}
					aria-checked={importance === level}
					disabled={level > 0 && !ready}
					onclick={() => (importance = level)}>{importanceName(level)}</button
				>
			{/each}
		</div>
	</div>
	{@render children()}
	<p class="wish-card__rule">{rule}</p>
</div>

<style>
	.wish-card {
		display: flex;
		flex-direction: column;
		gap: var(--space-2);
		padding: var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-card);
	}

	.wish-card--on {
		border-color: var(--color-olive);
	}

	.wish-card__head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-3);
	}

	.wish-card__levels {
		display: inline-flex;
	}

	.wish-card__level {
		margin-left: -1px;
		padding: var(--space-1) var(--space-2);
		border: 1px solid var(--color-line);
		background: var(--color-ground);
		color: inherit;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.wish-card__level:first-child {
		margin-left: 0;
		border-radius: var(--radius-full) 0 0 var(--radius-full);
	}

	.wish-card__level:last-child {
		border-radius: 0 var(--radius-full) var(--radius-full) 0;
	}

	.wish-card__level--on {
		position: relative;
		background: var(--color-olive);
		border-color: var(--color-olive);
		color: var(--color-ground);
	}

	.wish-card__level:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.wish-card__rule {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}
</style>
