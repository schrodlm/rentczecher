<script lang="ts">
	import type { RichText } from '$lib/i18n/messages';

	let { parts }: { parts: RichText } = $props();
</script>

{#each parts as part, index (index)}{#if typeof part === 'string'}{part}{:else if 'href' in part}<a
			href={part.href}>{part.text}</a
		>{:else}<span class="ui-label">{part.uiLabel}</span>{/if}{/each}

<style>
	.ui-label {
		white-space: nowrap;
		font-size: 0.9em;
		font-weight: 600;
		padding: 1px 7px;
		border: 1px solid var(--line-strong);
		border-radius: 5px;
		background: var(--bg);
	}
</style>
