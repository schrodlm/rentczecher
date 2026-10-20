import type { GalleryModel, SidecarClient } from '$lib/api/client';
import type { GalleryChangedEvent } from '$lib/api/events';

/* How long a flat stays selected before its whole gallery is asked for, so
stepping through the list asks for none of the flats passed over. */
export const LOOK_MS = 1000;

type ShownFlat = { profileId: string; propertyId: string };

/* The selected flat's gallery, loaded again whenever the engine says its
photos changed. A flat that stays selected a moment has its whole gallery
asked for. */
export class GalleryStore {
	gallery = $state<GalleryModel | null>(null);
	private shown: ShownFlat | null = null;
	private source: EventSource | null = null;
	private lookTimer: ReturnType<typeof setTimeout> | null = null;
	private loads = 0;

	constructor(private readonly client: Pick<SidecarClient, 'gallery' | 'requestGallery' | 'eventsUrl'>) {}

	connect(): void {
		this.disconnect();
		this.source = new EventSource(this.client.eventsUrl());
		this.source.addEventListener('gallery_changed', (event: MessageEvent<string>) => {
			const data: GalleryChangedEvent = JSON.parse(event.data);
			if (data.property_id === this.shown?.propertyId) void this.load(this.shown);
		});
	}

	disconnect(): void {
		this.source?.close();
		this.source = null;
		this.stopLooking();
	}

	show(shown: ShownFlat | null): void {
		this.stopLooking();
		this.gallery = null;
		this.shown = shown;
		if (shown === null) return;
		void this.load(shown);
		this.lookTimer = setTimeout(() => {
			// A refused request leaves the flat with its main photo.
			this.client.requestGallery(shown.profileId, shown.propertyId).catch(() => {});
		}, LOOK_MS);
	}

	private stopLooking(): void {
		if (this.lookTimer !== null) clearTimeout(this.lookTimer);
		this.lookTimer = null;
	}

	/* Only the latest load's answer counts, so an older one arriving late
	never replaces it, and a failed one shows no gallery. */
	private async load(shown: ShownFlat): Promise<void> {
		const load = ++this.loads;
		try {
			const gallery = await this.client.gallery(shown.profileId, shown.propertyId);
			if (load === this.loads && this.shown === shown) this.gallery = gallery;
		} catch {
			if (load === this.loads && this.shown === shown) this.gallery = null;
		}
	}
}
