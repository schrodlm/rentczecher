import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import type { GalleryModel } from '$lib/api/client';
import { FakeEventSource } from '$lib/test-support/fake-event-source';
import { GalleryStore, LOOK_MS } from './gallery.svelte';

function galleryOf(propertyId: string, photoCount: number): GalleryModel {
	return {
		status: 'stored',
		source: 'sreality',
		posting_url: `https://sreality.cz/detail/${propertyId}`,
		photo_count: photoCount,
		photos: [{ url: `http://127.0.0.1:1/v1/photos/${propertyId}.jpg` }]
	};
}

class FakeClient {
	galleries = new Map<string, GalleryModel>();
	requested: string[] = [];

	async gallery(_profileId: string, propertyId: string): Promise<GalleryModel> {
		const gallery = this.galleries.get(propertyId);
		if (gallery === undefined) throw new Error('404');
		return gallery;
	}

	async requestGallery(_profileId: string, propertyId: string): Promise<void> {
		this.requested.push(propertyId);
	}

	eventsUrl(): string {
		return 'http://127.0.0.1:1/v1/events';
	}
}

describe('GalleryStore', () => {
	beforeEach(() => {
		FakeEventSource.instances = [];
		vi.stubGlobal('EventSource', FakeEventSource);
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	test('loads the gallery of the flat shown', async () => {
		const client = new FakeClient();
		client.galleries.set('prop-1', galleryOf('prop-1', 1));
		const store = new GalleryStore(client);
		store.show({ profileId: 'p1', propertyId: 'prop-1' });
		await vi.waitFor(() => expect(store.gallery).toEqual(galleryOf('prop-1', 1)));
	});

	test('asks for the whole gallery of a flat shown for a moment', () => {
		const client = new FakeClient();
		const store = new GalleryStore(client);
		store.show({ profileId: 'p1', propertyId: 'prop-1' });
		vi.advanceTimersByTime(LOOK_MS);
		expect(client.requested).toEqual(['prop-1']);
	});

	test('asks for nothing for a flat passed over', () => {
		const client = new FakeClient();
		const store = new GalleryStore(client);
		store.show({ profileId: 'p1', propertyId: 'prop-1' });
		vi.advanceTimersByTime(LOOK_MS / 2);
		store.show({ profileId: 'p1', propertyId: 'prop-2' });
		vi.advanceTimersByTime(LOOK_MS);
		expect(client.requested).toEqual(['prop-2']);
	});

	test('loads the gallery again when its photos change', async () => {
		const client = new FakeClient();
		client.galleries.set('prop-1', galleryOf('prop-1', 1));
		const store = new GalleryStore(client);
		store.connect();
		store.show({ profileId: 'p1', propertyId: 'prop-1' });
		await vi.waitFor(() => expect(store.gallery?.photo_count).toBe(1));
		client.galleries.set('prop-1', galleryOf('prop-1', 5));
		FakeEventSource.instances[0].emit('gallery_changed', { property_id: 'prop-1' });
		await vi.waitFor(() => expect(store.gallery?.photo_count).toBe(5));
	});

	test('ignores a change to another flat\'s photos', async () => {
		const client = new FakeClient();
		client.galleries.set('prop-1', galleryOf('prop-1', 1));
		const store = new GalleryStore(client);
		store.connect();
		store.show({ profileId: 'p1', propertyId: 'prop-1' });
		await vi.waitFor(() => expect(store.gallery).not.toBeNull());
		const load = vi.spyOn(client, 'gallery');
		FakeEventSource.instances[0].emit('gallery_changed', { property_id: 'prop-2' });
		expect(load).not.toHaveBeenCalled();
	});

	test('drops an answer for a flat no longer shown', async () => {
		const client = new FakeClient();
		client.galleries.set('prop-1', galleryOf('prop-1', 1));
		const store = new GalleryStore(client);
		store.show({ profileId: 'p1', propertyId: 'prop-1' });
		store.show(null);
		await vi.runAllTimersAsync();
		expect(store.gallery).toBeNull();
	});

	test('keeps the latest answer when an older one arrives late', async () => {
		const client = new FakeClient();
		const answers: ((gallery: GalleryModel) => void)[] = [];
		client.gallery = () => new Promise((resolve) => answers.push(resolve));
		const store = new GalleryStore(client);
		store.connect();
		store.show({ profileId: 'p1', propertyId: 'prop-1' });
		FakeEventSource.instances[0].emit('gallery_changed', { property_id: 'prop-1' });
		answers[1](galleryOf('prop-1', 5));
		answers[0](galleryOf('prop-1', 1));
		await vi.runAllTimersAsync();
		expect(store.gallery?.photo_count).toBe(5);
	});

	test('asks for nothing once disconnected', () => {
		const client = new FakeClient();
		const store = new GalleryStore(client);
		store.show({ profileId: 'p1', propertyId: 'prop-1' });
		store.disconnect();
		vi.advanceTimersByTime(LOOK_MS);
		expect(client.requested).toEqual([]);
	});

	test('shows no gallery when it cannot be loaded', async () => {
		const store = new GalleryStore(new FakeClient());
		store.show({ profileId: 'p1', propertyId: 'prop-unknown' });
		await vi.runAllTimersAsync();
		expect(store.gallery).toBeNull();
	});
});
