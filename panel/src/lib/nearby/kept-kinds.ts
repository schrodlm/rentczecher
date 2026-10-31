import { NEARBY_KIND_ORDER, type NearbyKind } from './kinds';

const KEY_PREFIX = 'rentczecher.nearbyKinds.';

// The browser may refuse its storage, as in a private window, and then a
// profile simply shows no kinds.
export function keptNearbyKinds(profileId: string): NearbyKind[] {
	try {
		const kept: unknown = JSON.parse(localStorage.getItem(KEY_PREFIX + profileId) ?? '[]');
		if (!Array.isArray(kept)) return [];
		return NEARBY_KIND_ORDER.filter((kind) => kept.includes(kind));
	} catch {
		return [];
	}
}

export function keepNearbyKinds(profileId: string, kinds: readonly NearbyKind[]): void {
	try {
		localStorage.setItem(KEY_PREFIX + profileId, JSON.stringify(kinds));
	} catch {
		return;
	}
}
