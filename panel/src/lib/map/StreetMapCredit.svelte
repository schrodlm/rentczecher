<script lang="ts">
	import { opensInBrowser } from '$lib/browser-link';
	import { getTranslatorContext } from '$lib/i18n/context';

	/* The credit the OpenStreetMap tiles ask of every map showing them. */
	const t = getTranslatorContext();
</script>

<a
	class="street-map-credit"
	href="https://www.openstreetmap.org/copyright"
	target="_blank"
	rel="noopener noreferrer"
	use:opensInBrowser>© {t.t('OpenStreetMap contributors')}</a
>

<style>
	.street-map-credit {
		color: var(--color-bronze);
		font-size: 0.6875rem;
	}
</style>
