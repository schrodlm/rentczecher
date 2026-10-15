<script lang="ts">
	import type { Messages } from '$lib/i18n/messages';

	let { t }: { t: Messages } = $props();
</script>

<section>
	<div class="container inner">
		<h2 class="section-heading">{t.privacy.heading}</h2>
		<p>{t.privacy.body}</p>
	</div>
</section>

<style>
	section {
		background: var(--band);
		color: var(--band-text);
	}

	.inner {
		padding-top: 72px;
		padding-bottom: 72px;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr));
		gap: 32px;
		align-items: center;
	}

	p {
		font-size: 18px;
		line-height: 1.6;
	}
</style>
