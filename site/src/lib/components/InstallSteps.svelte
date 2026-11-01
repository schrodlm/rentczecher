<script lang="ts">
	import RichText from './RichText.svelte';
	import type { InstallStep } from '$lib/i18n/messages';

	let { steps }: { steps: InstallStep[] } = $props();
</script>

<ol>
	{#each steps as step, index (index)}
		<li>
			<p><RichText parts={step.text} /></p>
			{#if step.screenshot !== null}
				<img src="/install/{step.screenshot.file}" alt={step.screenshot.alt} loading="lazy" />
			{/if}
		</li>
	{/each}
</ol>

<style>
	ol {
		margin: 0;
		padding-left: 22px;
		display: flex;
		flex-direction: column;
		gap: 18px;
	}

	li::marker {
		font-weight: 700;
		color: var(--amber);
	}

	p {
		margin: 0;
	}

	img {
		display: block;
		margin-top: 12px;
		max-width: 100%;
		height: auto;
		border: 1px solid var(--line);
		border-radius: 8px;
		box-shadow: 0 4px 16px var(--shadow);
	}
</style>
