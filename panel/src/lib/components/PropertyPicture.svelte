<script lang="ts">
	import type { TrackedPropertyModel } from '$lib/api/client';
	import { sourceInitial } from '$lib/format';
	import { shownPortal } from '$lib/portals';

	/* A listing's picture: its main photo, or a plain tile with a house while
	it has none, the portal's logo small on the corner. It fills the box its
	parent gives it. */
	let { listing }: { listing: TrackedPropertyModel } = $props();

	const portal = $derived(shownPortal(listing.source));
	// A photo whose file is gone, or whose link died with an engine restart,
	// falls back to the tile rather than the browser's broken image.
	let failedUrl = $state<string | null>(null);
	const photoUrl = $derived(
		listing.main_photo !== null && listing.main_photo.url !== failedUrl ? listing.main_photo.url : null
	);
</script>

<span class="property-picture">
	{#if photoUrl !== null}
		<img class="property-picture__photo" src={photoUrl} alt="" onerror={() => (failedUrl = photoUrl)} />
	{:else}
		<span class="property-picture__none">
			<svg viewBox="0 0 24 24" aria-hidden="true">
				<path d="M3 11.5 12 4l9 7.5M5.5 9.5V20h13V9.5M10 20v-5h4v5" />
			</svg>
		</span>
	{/if}
	<span class="property-picture__portal">
		{#if portal}<img src={portal.logo} alt="" />{:else}{sourceInitial(listing.source)}{/if}
	</span>
</span>

<style>
	.property-picture {
		position: relative;
		display: block;
		width: 100%;
		height: 100%;
	}

	.property-picture__photo,
	.property-picture__none {
		display: block;
		width: 100%;
		height: 100%;
		border-radius: var(--radius-sm);
	}

	.property-picture__photo {
		object-fit: cover;
	}

	.property-picture__none {
		display: grid;
		place-items: center;
		background: var(--color-line);
	}

	.property-picture__none svg {
		width: 55%;
		height: 55%;
		fill: none;
		stroke: var(--color-bronze);
		stroke-width: 1.5;
		stroke-linecap: round;
		stroke-linejoin: round;
		opacity: 0.6;
	}

	.property-picture__portal {
		position: absolute;
		right: -3px;
		bottom: -3px;
		display: grid;
		place-items: center;
		width: 34%;
		height: 34%;
		border: 2px solid var(--color-ground);
		border-radius: var(--radius-sm);
		background: var(--color-card);
		color: var(--color-bronze);
		font-size: 0.5rem;
		font-weight: 700;
	}

	.property-picture__portal img {
		width: 100%;
		height: 100%;
		border-radius: inherit;
		object-fit: contain;
	}
</style>
