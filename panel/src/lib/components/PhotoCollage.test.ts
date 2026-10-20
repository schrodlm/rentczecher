import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import type { GalleryModel } from '$lib/api/client';
import { renderWithTranslator } from '$lib/test-support/render';
import PhotoCollage from './PhotoCollage.svelte';

function galleryOf(status: GalleryModel['status'], stored: number, photoCount = stored): GalleryModel {
	return {
		status,
		source: 'sreality',
		posting_url: 'https://sreality.cz/detail/1',
		photo_count: photoCount,
		photos: Array.from({ length: stored }, (_, index) => ({ url: `http://127.0.0.1:1/${index}.jpg` }))
	};
}

function collage(gallery: GalleryModel) {
	return renderWithTranslator(PhotoCollage, { gallery });
}

function tiles(container: HTMLElement) {
	return {
		photos: container.querySelectorAll('button.photo-collage__tile').length,
		waiting: container.querySelectorAll('.photo-collage__tile--waiting').length,
		shape: container.querySelector('.photo-collage')?.className.match(/photo-collage--(\d)/)?.[1] ?? null
	};
}

describe('PhotoCollage', () => {
	test.each([1, 2, 3, 4, 5])('shapes itself for %i photos', async (count) => {
		const { container } = await collage(galleryOf('stored', count));
		expect(tiles(container)).toEqual({ photos: count, waiting: 0, shape: String(count) });
	});

	test('shows five photos at most and says how many more there are', async () => {
		const { container, getByText } = await collage(galleryOf('stored', 12));
		expect(tiles(container).photos).toBe(5);
		expect(getByText('+7 fotek')).toBeInTheDocument();
	});

	test('waits for the photos a downloading gallery will have', async () => {
		const { container } = await collage(galleryOf('downloading', 1, 8));
		expect(tiles(container)).toEqual({ photos: 1, waiting: 4, shape: '5' });
	});

	test('waits for one more photo while a gallery of known photos still downloads', async () => {
		const { container } = await collage(galleryOf('downloading', 1, 1));
		expect(tiles(container)).toEqual({ photos: 1, waiting: 1, shape: '2' });
	});

	test('says in the whole window that more photos are downloading', async () => {
		const { getByLabelText, getByText } = await collage(galleryOf('downloading', 1, 1));
		await fireEvent.click(getByLabelText('Fotka 1'));
		expect(getByText('Stahuji další fotky…')).toBeInTheDocument();
	});

	test('waits for at least one photo while the gallery is found out', async () => {
		const { container } = await collage(galleryOf('downloading', 0, 0));
		expect(tiles(container)).toEqual({ photos: 0, waiting: 1, shape: '1' });
	});

	test('counts only the stored photos once downloading is over', async () => {
		const { container, queryByText } = await collage(galleryOf('stored', 2, 6));
		expect(tiles(container).photos).toBe(2);
		expect(queryByText(/\+\d/)).toBeNull();
	});

	test('says when a listing has no photos', async () => {
		const { getByText } = await collage(galleryOf('none', 0));
		expect(getByText('Inzerát nemá fotky')).toBeInTheDocument();
	});

	test('says when the photos could not be downloaded', async () => {
		const { getByText } = await collage(galleryOf('failed', 0, 3));
		expect(getByText('Fotky se zatím nepodařilo stáhnout')).toBeInTheDocument();
	});

	test('opens the whole window on the photo picked', async () => {
		const { container, getByLabelText, getByRole } = await collage(galleryOf('stored', 3));
		await fireEvent.click(getByLabelText('Fotka 2'));
		expect(getByRole('dialog')).toBeInTheDocument();
		expect(container.ownerDocument.querySelector('.photo-viewer__photo')).toHaveAttribute(
			'src',
			'http://127.0.0.1:1/1.jpg'
		);
	});

	test('closes the whole window when its photo leaves the gallery', async () => {
		const { getByLabelText, queryByRole, rerender } = await collage(galleryOf('stored', 3));
		await fireEvent.click(getByLabelText('Fotka 3'));
		expect(queryByRole('dialog')).not.toBeNull();
		await rerender({ gallery: galleryOf('downloading', 1, 8) });
		expect(queryByRole('dialog')).toBeNull();
	});
});
