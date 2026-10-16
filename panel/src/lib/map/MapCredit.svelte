<script lang="ts">
	import { opensInBrowser } from '$lib/browser-link';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { MAP_CREDIT, MAP_CREDIT_LICENSE, MAP_CREDIT_TERMS } from './czech-map';

	/* The credit every view of the RÚIAN-derived map carries: ČÚZK and the
	dataset's year, their terms, the license, and that the data was changed. */
	const t = getTranslatorContext();
</script>

<span
	class="map-credit"
	title={t.t('RÚIAN place data, modified: names and centre points kept, outlines traced from the centre points')}
>
	<a href={MAP_CREDIT_TERMS} target="_blank" rel="noopener noreferrer" use:opensInBrowser>{MAP_CREDIT}</a>,
	<a href={MAP_CREDIT_LICENSE} target="_blank" rel="noopener noreferrer" use:opensInBrowser>CC BY 4.0</a>
</span>

<style>
	.map-credit {
		color: var(--color-bronze);
		font-size: 0.6875rem;
	}

	.map-credit a {
		color: inherit;
	}
</style>
