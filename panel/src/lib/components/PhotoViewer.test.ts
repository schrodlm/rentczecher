import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import PhotoViewer from './PhotoViewer.svelte';

const PHOTOS = ['http://127.0.0.1:1/a.jpg', 'http://127.0.0.1:1/b.jpg', 'http://127.0.0.1:1/c.jpg'];

function viewer(photos: readonly string[], current: number, onclose = () => {}, downloading = false) {
	return renderWithTranslator(PhotoViewer, {
		photos,
		current,
		downloading,
		portalName: 'Sreality',
		postingUrl: 'https://sreality.cz/detail/1',
		onclose
	});
}

function shownPhoto(container: HTMLElement): string | null {
	return container.querySelector('.photo-viewer__photo')?.getAttribute('src') ?? null;
}

describe('PhotoViewer', () => {
	test('shows the photo it opened on and where it is among them', async () => {
		const { container, getByText } = await viewer(PHOTOS, 1);
		expect(shownPhoto(container)).toBe(PHOTOS[1]);
		expect(getByText('2 / 3')).toBeInTheDocument();
	});

	test('steps with the arrows, round from the last to the first', async () => {
		const { container } = await viewer(PHOTOS, 2);
		await fireEvent.keyDown(window, { key: 'ArrowRight' });
		expect(shownPhoto(container)).toBe(PHOTOS[0]);
		await fireEvent.keyDown(window, { key: 'ArrowLeft' });
		expect(shownPhoto(container)).toBe(PHOTOS[2]);
	});

	test('steps with its buttons', async () => {
		const { container, getByLabelText } = await viewer(PHOTOS, 0);
		await fireEvent.click(getByLabelText('Další fotka'));
		expect(shownPhoto(container)).toBe(PHOTOS[1]);
		await fireEvent.click(getByLabelText('Předchozí fotka'));
		expect(shownPhoto(container)).toBe(PHOTOS[0]);
	});

	test('closes with Escape and with its button', async () => {
		const onclose = vi.fn();
		const { getByLabelText } = await viewer(PHOTOS, 0, onclose);
		await fireEvent.keyDown(window, { key: 'Escape' });
		await fireEvent.click(getByLabelText('Zavřít'));
		expect(onclose).toHaveBeenCalledTimes(2);
	});

	test('names the portal the photos come from and links to the posting', async () => {
		const { getByText } = await viewer(PHOTOS, 0);
		expect(getByText(/Foto: Sreality/).closest('a')).toHaveAttribute('href', 'https://sreality.cz/detail/1');
	});

	test('says while more photos are downloading', async () => {
		const { getByText } = await viewer(PHOTOS.slice(0, 1), 0, () => {}, true);
		expect(getByText('Stahuji další fotky…')).toBeInTheDocument();
	});

	test('says nothing more once the photos are down', async () => {
		const { queryByText } = await viewer(PHOTOS, 0);
		expect(queryByText('Stahuji další fotky…')).toBeNull();
	});

	test('offers no steps for a single photo', async () => {
		const { queryByLabelText } = await viewer(PHOTOS.slice(0, 1), 0);
		expect(queryByLabelText('Další fotka')).toBeNull();
	});

	test('is a modal dialog, so the list behind it keeps no keys', async () => {
		const { getByRole } = await viewer(PHOTOS, 0);
		expect(getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
	});
});
