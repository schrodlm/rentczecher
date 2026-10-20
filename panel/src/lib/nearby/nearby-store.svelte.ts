import { boxAround, nearest, type Box, type NearbyPlace, type Nearest, type Point } from './geometry';
import { NEARBY_KIND_ORDER, NEARBY_KINDS, type NearbyKind } from './kinds';
import type { OverpassClient } from './overpass';

// Far enough that a flat at the edge of the profile's area still finds the
// stop just outside it.
const MARGIN_M = 1500;
// A kind none of the servers answered is asked for again after a minute.
const RETRY_MS = 60_000;
const KEY_PREFIX = 'rentczecher.nearbyKinds.';

type Found = { box: Box; places: NearbyPlace[] };
export type KindDistance = { kind: NearbyKind; distanceM: number };

/* The kinds of place a profile shows near its flats, kept on this machine,
and the places of each, asked of Overpass for the area around the
profile's flats and held only while the app runs. A kind not answered yet,
or whose servers are busy, shows nothing. */
export class NearbyStore {
	chosen = $state<NearbyKind[]>([]);
	private found = $state.raw<Map<NearbyKind, Found>>(new Map());
	private profileId: string | null = null;
	private box: Box | null = null;
	// The profile each kind is being asked for, so a request still out for a
	// profile left behind never holds up the one shown.
	private loading = new Map<NearbyKind, string>();
	// Every row asks for its distances on each render, so each is worked out
	// once per answer.
	private nearestCache = new Map<string, Nearest | null>();

	constructor(private readonly client: Pick<OverpassClient, 'places'>) {}

	show(profileId: string, points: readonly Point[]): void {
		if (profileId !== this.profileId) {
			this.profileId = profileId;
			this.setFound(new Map());
			this.chosen = chosenKinds(profileId);
		}
		this.box = boxAround(points, MARGIN_M);
		for (const kind of this.chosen) void this.load(kind);
	}

	toggle(kind: NearbyKind): void {
		if (this.profileId === null) return;
		const chosen = this.chosen.includes(kind) ? this.chosen.filter((each) => each !== kind) : [...this.chosen, kind];
		// Kept in the list's order, whatever order they were switched on in.
		this.chosen = NEARBY_KIND_ORDER.filter((each) => chosen.includes(each));
		keepChosenKinds(this.profileId, this.chosen);
		if (this.chosen.includes(kind)) void this.load(kind);
	}

	/* How far the nearest place of each of the first kinds lies, leaving out
	the kinds not answered yet. */
	distancesFrom(point: Point, most: number): KindDistance[] {
		return this.chosen.slice(0, most).flatMap((kind) => {
			const found = this.nearestTo(point, kind);
			return found === null ? [] : [{ kind, distanceM: found.distanceM }];
		});
	}

	nearestTo(point: Point, kind: NearbyKind): Nearest | null {
		const found = this.found.get(kind);
		if (found === undefined) return null;
		const key = `${kind}:${point.lat},${point.lon}`;
		const cached = this.nearestCache.get(key);
		if (cached !== undefined) return cached;
		const answer = nearest(point, found.places);
		this.nearestCache.set(key, answer);
		return answer;
	}

	private async load(kind: NearbyKind): Promise<void> {
		const box = this.box;
		const profileId = this.profileId;
		if (box === null || profileId === null || this.loading.get(kind) === profileId) return;
		const known = this.found.get(kind);
		if (known !== undefined && contains(known.box, box)) return;
		const shown = NEARBY_KINDS.find((each) => each.kind === kind)!;
		this.loading.set(kind, profileId);
		let places: NearbyPlace[];
		try {
			places = await this.client.places(shown, box);
		} catch {
			setTimeout(() => this.retry(kind, profileId), RETRY_MS);
			return;
		} finally {
			if (this.loading.get(kind) === profileId) this.loading.delete(kind);
		}
		if (profileId !== this.profileId) return;
		this.setFound(new Map(this.found).set(kind, { box, places }));
		// The flats may have spread while the answer came, and this asks again
		// only if they did.
		void this.load(kind);
	}

	private retry(kind: NearbyKind, profileId: string): void {
		if (profileId === this.profileId && this.chosen.includes(kind)) void this.load(kind);
	}

	private setFound(found: Map<NearbyKind, Found>): void {
		this.found = found;
		this.nearestCache = new Map();
	}
}

function contains(outer: Box, inner: Box): boolean {
	return outer.south <= inner.south && outer.west <= inner.west && outer.north >= inner.north && outer.east >= inner.east;
}

// The browser may refuse its storage, as in a private window, and then a
// profile simply shows no kinds.
function chosenKinds(profileId: string): NearbyKind[] {
	try {
		const kept: unknown = JSON.parse(localStorage.getItem(KEY_PREFIX + profileId) ?? '[]');
		if (!Array.isArray(kept)) return [];
		return NEARBY_KIND_ORDER.filter((kind) => kept.includes(kind));
	} catch {
		return [];
	}
}

function keepChosenKinds(profileId: string, kinds: readonly NearbyKind[]): void {
	try {
		localStorage.setItem(KEY_PREFIX + profileId, JSON.stringify(kinds));
	} catch {
		return;
	}
}
