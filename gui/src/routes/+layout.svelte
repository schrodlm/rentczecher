<script lang="ts">
	import '$lib/styles/tokens.css';
	import '$lib/styles/base.css';
	import logo from '$lib/assets/logo.svg';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<svelte:head>
	<link rel="icon" href={logo} />
</svelte:head>

{@render children()}
