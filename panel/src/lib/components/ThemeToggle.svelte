<script lang="ts">
	import { MediaQuery } from 'svelte/reactivity';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { themeName } from '$lib/theme';
	import type { Theme } from '$lib/user-config';
	import ThemeIcon from './ThemeIcon.svelte';

	/* The top bar's switch between light and dark. It shows the theme on
	screen, the system's while the user config follows it, and a click turns
	it to the other one. */
	let { theme, onchange }: { theme: Theme; onchange: (theme: Theme) => void } = $props();

	const t = getTranslatorContext();
	const systemDark = new MediaQuery('(prefers-color-scheme: dark)');

	const shown = $derived(theme !== 'system' ? theme : systemDark.current ? 'dark' : 'light');
	const label = $derived(t.t('Appearance: {name}', { name: themeName(shown, t) }));
</script>

<button
	type="button"
	class="theme-toggle"
	title={label}
	aria-label={label}
	onclick={() => onchange(shown === 'dark' ? 'light' : 'dark')}
>
	<ThemeIcon theme={shown} />
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
