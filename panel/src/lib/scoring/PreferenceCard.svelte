<script lang="ts">
	import '$lib/styles/preferences.css';
	import type { Snippet } from 'svelte';
	import type { Wish } from './wishes';

	/* One preference: switched on or off, its share of the score while on, the
	setting it scores against and the rule it scores by. Until the setting is
	chosen it cannot be switched on. */
	let {
		wish,
		title,
		on,
		weight,
		ready,
		rule,
		ontoggle,
		children
	}: {
		wish: Wish;
		title: string;
		on: boolean;
		weight: number;
		ready: boolean;
		rule: string;
		ontoggle: () => void;
		children: Snippet;
	} = $props();
</script>

<div class="preference-card preference-{wish}" class:preference-card--off={!on}>
	<div class="preference-card__head">
		<button
			type="button"
			class="preference-card__switch"
			class:preference-card__switch--on={on}
			role="switch"
			aria-checked={on}
			aria-label={title}
			disabled={!on && !ready}
			onclick={ontoggle}
		>
			<i class="preference-card__knob"></i>
		</button>
		<strong class="preference-card__title">{title}</strong>
		{#if on}
			<span class="preference-card__share">{weight} %</span>
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

	.preference-card__switch {
		position: relative;
		flex: none;
		width: 2.25rem;
		height: 1.25rem;
		padding: 0;
		border: none;
		border-radius: var(--radius-full);
		background: var(--color-line);
		cursor: pointer;
	}

	.preference-card__switch--on {
		background: var(--color-olive);
	}

	.preference-card__switch:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.preference-card__knob {
		position: absolute;
		inset: 2px auto 2px 2px;
		aspect-ratio: 1;
		border-radius: 50%;
		background: var(--color-card);
		transition: transform 120ms ease-out;
	}

	.preference-card__switch--on .preference-card__knob {
		transform: translateX(1rem);
	}

	.preference-card__rule {
		margin: 0;
		color: var(--color-bronze);
		font-size: 0.8125rem;
	}
</style>
