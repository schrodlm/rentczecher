import { fireEvent } from '@testing-library/svelte';
import { describe, expect, test } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import { trackedProperty } from '$lib/test-support/tracked-property';
import PropertyPicture from './PropertyPicture.svelte';

describe('PropertyPicture', () => {
	test('shows the main photo with its portal on the corner', async () => {
		const { container } = await renderWithTranslator(PropertyPicture, {
			listing: trackedProperty('a', { source: 'sreality', main_photo: { url: 'http://127.0.0.1:1/a.jpg?sig=s' } })
		});
		expect(container.querySelector('.property-picture__photo')).toHaveAttribute('src', 'http://127.0.0.1:1/a.jpg?sig=s');
		expect(container.querySelector('.property-picture__portal img')).not.toBeNull();
	});

	test('shows a plain tile with a house while there is no photo', async () => {
		const { container } = await renderWithTranslator(PropertyPicture, {
			listing: trackedProperty('a', { main_photo: null })
		});
		expect(container.querySelector('.property-picture__photo')).toBeNull();
		expect(container.querySelector('.property-picture__none svg')).not.toBeNull();
	});

	test('marks a portal it does not know by its initial', async () => {
		const { container } = await renderWithTranslator(PropertyPicture, {
			listing: trackedProperty('a', { source: 'idnes', main_photo: null })
		});
		expect(container.querySelector('.property-picture__portal')).toHaveTextContent('I');
	});

	test('falls back to the tile when the photo cannot be loaded', async () => {
		const { container } = await renderWithTranslator(PropertyPicture, {
			listing: trackedProperty('a', { main_photo: { url: 'http://127.0.0.1:1/gone.jpg?sig=s' } })
		});
		await fireEvent.error(container.querySelector('.property-picture__photo')!);
		expect(container.querySelector('.property-picture__photo')).toBeNull();
		expect(container.querySelector('.property-picture__none svg')).not.toBeNull();
	});
});
