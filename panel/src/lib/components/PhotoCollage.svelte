<script lang="ts">
	import type { GalleryModel } from '$lib/api/client';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { shownPortal } from '$lib/portals';
	import PhotoViewer from './PhotoViewer.svelte';

	const MOST_TILES = 5;

	/* A flat's first photos, shaped by how many there are, the last tile
	counting the rest. */
	let { gallery }: { gallery: GalleryModel } = $props();

	const t = getTranslatorContext();

	let opened = $state<number | null>(null);

	const portal = $derived(shownPortal(gallery.source));
	const photos = $derived(gallery.photos.map((photo) => photo.url));
	const downloading = $derived(gallery.status === 'downloading');
	// A gallery still downloading shows the photos it will have, at least one
	// more than it has, the others the ones it has.
	const total = $derived(downloading ? Math.max(gallery.photo_count, photos.length + 1) : photos.length);
	const tiles = $derived(Math.min(total, MOST_TILES));
	const more = $derived(total - tiles);

	// A reload can leave the gallery with fewer photos than the one open.
	$effect(() => {
		if (opened !== null && opened >= photos.length) opened = null;
	});
</script>

{#if tiles === 0}
	<div class="photo-collage__empty">
		{#if portal}<img src={portal.logo} alt="" />{/if}
		<p>
			{gallery.status === 'failed' ? t.t('The photos could not be downloaded yet') : t.t('This listing has no photos')}
		</p>
	</div>
{:else}
	<div class="photo-collage photo-collage--{tiles}">
		{#each { length: tiles }, index (index)}
			{#if index < photos.length}
				<button
					type="button"
					class="photo-collage__tile"
					aria-label={t.t('Photo {number}', { number: index + 1 })}
					onclick={() => (opened = index)}
				>
					<img src={photos[index]} alt="" />
					{#if index === tiles - 1 && more > 0}
						<span class="photo-collage__more">{t.tn('+{count} photo', '+{count} photos', more)}</span>
					{/if}
				</button>
			{:else}
				<span class="photo-collage__tile photo-collage__tile--waiting" style:--delay="{index * -0.55}s"></span>
			{/if}
		{/each}
	</div>
{/if}

{#if opened !== null}
	<PhotoViewer
		{photos}
		bind:current={opened}
		{downloading}
		portalName={portal?.name ?? gallery.source}
		postingUrl={gallery.posting_url}
		onclose={() => (opened = null)}
	/>
{/if}

<style>
	/* Tiles of mixed spans on a four-column grid, the main photo always the
	largest on the left. */
	.photo-collage {
		display: grid;
		gap: 6px;
		grid-template-columns: repeat(4, 1fr);
		margin: 0 auto;
		overflow: hidden;
		border-radius: var(--radius-md);
		aspect-ratio: 12 / 5;
		/* As wide as the details, but never taller than 40 % of the window. */
		width: min(100%, 40vh * 12 / 5);
	}

	.photo-collage--1 .photo-collage__tile {
		grid-column: span 4;
	}

	.photo-collage--2 .photo-collage__tile {
		grid-column: span 2;
	}

	/* The tall main photo with two wide ones beside it. */
	.photo-collage--3 {
		grid-template-rows: repeat(2, 1fr);
	}

	.photo-collage--3 .photo-collage__tile {
		grid-column: span 2;
	}

	.photo-collage--3 .photo-collage__tile:first-child {
		grid-row: span 2;
	}

	/* The tall main photo, a wide one beside it and two small ones under. */
	.photo-collage--4 {
		grid-template-rows: repeat(2, 1fr);
	}

	.photo-collage--4 .photo-collage__tile:nth-child(1) {
		grid-column: span 2;
		grid-row: span 2;
	}

	.photo-collage--4 .photo-collage__tile:nth-child(2) {
		grid-column: span 2;
	}

	/* The tall main photo, then a wide one, a tall one and two small ones. */
	.photo-collage--5 {
		grid-template-rows: repeat(3, 1fr);
	}

	.photo-collage--5 .photo-collage__tile:nth-child(1) {
		grid-column: span 2;
		grid-row: span 3;
	}

	.photo-collage--5 .photo-collage__tile:nth-child(2) {
		grid-column: span 2;
	}

	.photo-collage--5 .photo-collage__tile:nth-child(3) {
		grid-row: span 2;
	}

	.photo-collage__tile {
		position: relative;
		min-height: 0;
		padding: 0;
		overflow: hidden;
		border: none;
		background: var(--color-card);
		cursor: zoom-in;
	}

	.photo-collage__tile img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		transition: transform 0.3s ease;
		animation: photo-collage-appear 0.5s ease-out;
	}

	.photo-collage__tile:hover img {
		transform: scale(1.04);
	}

	.photo-collage__more {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
		background: rgb(0 0 0 / 45%);
		color: #fff;
		font-size: 1.125rem;
		font-weight: 700;
	}

	/* Each waiting tile is its own blurred wash, breathing out of step with
	the others. The wash overflows the tile so the tile's clip, not the blur,
	draws its edge. */
	.photo-collage__tile--waiting {
		opacity: 0.6;
		animation: photo-collage-breathe 2.8s ease-in-out infinite;
		animation-delay: var(--delay);
		cursor: default;
	}

	.photo-collage__tile--waiting::before {
		position: absolute;
		inset: -24px;
		background:
			radial-gradient(circle at 25% 30%, var(--color-amber) 0, transparent 60%),
			radial-gradient(circle at 80% 75%, var(--color-olive) 0, transparent 65%),
			color-mix(in srgb, var(--color-line) 60%, var(--color-card));
		filter: blur(18px);
		content: '';
	}

	.photo-collage__empty {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-3);
		padding: var(--space-6);
		border: 1px dashed var(--color-line);
		border-radius: var(--radius-md);
		color: var(--color-bronze);
	}

	.photo-collage__empty img {
		width: 2.25rem;
		height: 2.25rem;
		opacity: 0.8;
	}

	.photo-collage__empty p {
		margin: 0;
	}

	@keyframes photo-collage-breathe {
		0%,
		100% {
			opacity: 0.4;
		}
		50% {
			opacity: 0.8;
		}
	}

	@keyframes photo-collage-appear {
		from {
			opacity: 0;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.photo-collage__tile--waiting,
		.photo-collage__tile img {
			animation: none;
			transition: none;
		}
	}
</style>
