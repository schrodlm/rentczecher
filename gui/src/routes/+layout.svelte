<script lang="ts">
	import '$lib/styles/tokens.css';
	import '$lib/styles/base.css';
	import logo from '$lib/assets/logo.svg';
	import { setTranslatorContext } from '$lib/i18n/context';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	// setContext must run once, synchronously, during component init. This
	// page never re-runs its load function, so the initial value is final.
	// svelte-ignore state_referenced_locally
	setTranslatorContext(data.translator);
</script>

<svelte:head>
	<link rel="icon" href={logo} />
</svelte:head>

{@render children()}
