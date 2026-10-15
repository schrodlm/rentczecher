<script lang="ts">
	import Icon from './Icon.svelte';
	import type { Messages } from '$lib/i18n/messages';

	let { t }: { t: Messages } = $props();

	let isDark = $state(false);

	// Until the visitor picks a theme, the page follows the system one.
	$effect(() => {
		const systemDark = matchMedia('(prefers-color-scheme: dark)');
		const sync = () => {
			const saved = document.documentElement.dataset.theme;
			isDark = saved ? saved === 'dark' : systemDark.matches;
		};
		sync();
		systemDark.addEventListener('change', sync);
		return () => systemDark.removeEventListener('change', sync);
	});

	function toggle() {
		isDark = !isDark;
		const theme = isDark ? 'dark' : 'light';
		document.documentElement.dataset.theme = theme;
		try {
			localStorage.setItem('theme', theme);
		} catch {
			// Storage can be blocked, the choice then lasts only for this page view.
		}
	}
</script>

<button type="button" class="iconbtn" aria-label={isDark ? t.theme.toLight : t.theme.toDark} onclick={toggle}>
	<Icon name={isDark ? 'sun' : 'moon'} />
</button>
