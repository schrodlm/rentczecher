<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';
	import { THEMES, type Theme } from '$lib/user-config';
	import ThemeIcon from './ThemeIcon.svelte';

	let { theme, onchange }: { theme: Theme; onchange: (theme: Theme) => void } = $props();

	const t = getTranslatorContext();

	const label = $derived(t.t('Appearance: {name}', { name: themeName() }));

	function themeName(): string {
		if (theme === 'light') return t.t('Light');
		if (theme === 'dark') return t.t('Dark');
		return t.t('Follow the system');
	}

	function next(): void {
		onchange(THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length]);
	}
</script>

<button type="button" class="theme-toggle" title={label} aria-label={label} onclick={next}>
	<ThemeIcon {theme} />
</button>

<style>
	.theme-toggle {
		display: grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		padding: 0;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-full);
		background: var(--color-ground);
		color: var(--color-ink);
		font-size: 1rem;
		cursor: pointer;
	}

	.theme-toggle:hover {
		border-color: var(--color-bronze);
	}
</style>
