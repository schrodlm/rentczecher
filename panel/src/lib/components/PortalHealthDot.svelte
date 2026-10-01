<script lang="ts">
	import { getTranslatorContext } from '$lib/i18n/context';

	let { portal, status }: { portal: string; status: 'ok' | 'broken' | 'zero_results' } = $props();

	const t = getTranslatorContext();

	// The five-color palette has no danger color, so a broken portal reads
	// as a hollow ring rather than an invented red dot.
	const statusLabel = $derived(
		status === 'ok'
			? t.t('working')
			: status === 'zero_results'
				? t.t('no results')
				: t.t('unreachable')
	);
</script>

<span class="dot dot--{status}" title="{portal}: {statusLabel}" aria-label="{portal}: {statusLabel}"
></span>

<style>
	.dot {
		display: inline-block;
		width: 0.625rem;
		height: 0.625rem;
		border-radius: var(--radius-full);
		box-sizing: border-box;
	}

	.dot--ok {
		background: var(--color-olive);
	}

	.dot--zero_results {
		background: var(--color-bronze);
	}

	.dot--broken {
		background: transparent;
		border: 2px solid var(--color-line);
	}
</style>
