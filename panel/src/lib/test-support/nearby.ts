import { NearbyStore } from '$lib/nearby/nearby-store.svelte';

/* A store whose Overpass finds nothing, for components that show nearby
places without a test asking about them. */
export function quietNearby(): NearbyStore {
	return new NearbyStore({ places: async () => [] });
}
