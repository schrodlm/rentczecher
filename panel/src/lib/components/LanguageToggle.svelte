<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { LANGUAGES, type Language } from '$lib/user-config';
	import Flag from './Flag.svelte';

	/* The top bar's choice of language, each named in its own language. */
	let { language, onchange }: { language: Language; onchange: (language: Language) => void } = $props();

	const t = getTranslatorContext();

	const OWN_NAMES: Record<Language, string> = { cs: 'Čeština', en: 'English' };
</script>

<div class="language-toggle" role="group" aria-label={t.t('Language')}>
	{#each LANGUAGES as each (each)}
		<button
			type="button"
			class="language-toggle__option"
			class:language-toggle__option--on={each === language}
			aria-pressed={each === language}
			title={OWN_NAMES[each]}
			onclick={() => {
				if (each !== language) onchange(each);
			}}
		>
			<span class="language-toggle__flag"><Flag language={each} /></span>
			{each.toUpperCase()}
		</button>
	{/each}
</div>

<style>
	.language-toggle {
		display: flex;
		overflow: hidden;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
	}

	.language-toggle__option {
		display: flex;
		align-items: center;
		gap: var(--space-1);
		padding: var(--space-1) var(--space-2);
		border: none;
		background: var(--color-ground);
		color: var(--color-bronze);
		font-size: 0.75rem;
		font-weight: 600;
		cursor: pointer;
	}

	.language-toggle__option--on {
		background: var(--color-olive);
		color: var(--color-ground);
	}

	.language-toggle__flag {
		height: 0.7rem;
	}
</style>
