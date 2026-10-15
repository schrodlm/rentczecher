<script lang="ts">
	import RichText from './RichText.svelte';
	import type { Messages } from '$lib/i18n/messages';

	let { t }: { t: Messages } = $props();
</script>

<section id="faq" class="container">
	<h2 class="section-heading">{t.faq.heading}</h2>
	{#each t.faq.items as item, index (index)}
		<details open={index === 0}>
			<summary>{item.question}</summary>
			<p><RichText parts={item.answer} /></p>
		</details>
	{/each}
</section>

<style>
	section {
		padding-bottom: 96px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	h2 {
		margin-bottom: 8px;
	}

	details {
		border-bottom: 1px solid var(--line);
	}

	summary {
		cursor: pointer;
		font-weight: 650;
		font-size: 18px;
		padding: 18px 0;
	}

	p {
		margin: 0 0 18px;
		line-height: 1.6;
		max-width: 62ch;
	}
</style>
