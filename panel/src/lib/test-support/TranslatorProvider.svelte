<script lang="ts">
	import { setTranslatorContext } from '$lib/i18n/context';
	import { Translator } from '$lib/i18n/translator';
	import type { Snippet } from 'svelte';

	let { translator, children }: { translator: Translator; children: Snippet } = $props();

	// svelte-ignore state_referenced_locally
	setTranslatorContext(translator);
</script>

{@render children()}
