import type { Box, NearbyPlace } from './geometry';
import type { NearbyKindShown } from './kinds';

// The public instances are run by volunteers and are often full, so the next
// answers when one is busy. A busy one may also sit on a request rather than
// refuse it, so each gets only a few seconds before the next is asked.
const SERVERS = [
	'https://overpass-api.de/api/interpreter',
	'https://overpass.private.coffee/api/interpreter',
	'https://overpass.kumi.systems/api/interpreter'
];
const WAIT_MS = 6000;

type OverpassElement = { lat?: number; lon?: number; center?: { lat: number; lon: number }; tags?: { name?: string } };

/* Asks OpenStreetMap's Overpass for the places of a kind inside a box. */
export class OverpassClient {
	constructor(private readonly fetchFn: typeof fetch = fetch) {}

	/* Throws when no server answers. */
	async places(kind: NearbyKindShown, box: Box): Promise<NearbyPlace[]> {
		const bounds = `(${box.south},${box.west},${box.north},${box.east})`;
		const query = `[out:json][timeout:25];(${kind.filters.map((filter) => filter + bounds).join(';')};);out center tags;`;
		for (const server of SERVERS) {
			// The limit covers waiting for the server to start answering, not
			// the download of a large answer once it has.
			const waiting = new AbortController();
			const timer = setTimeout(() => waiting.abort(), WAIT_MS);
			try {
				const response = await this.fetchFn(server, {
					method: 'POST',
					body: new URLSearchParams({ data: query }),
					signal: waiting.signal
				});
				clearTimeout(timer);
				if (!response.ok) continue;
				const answer: { elements: OverpassElement[] } = await response.json();
				return answer.elements.flatMap((element) => placeOf(element));
			} catch {
				continue;
			} finally {
				clearTimeout(timer);
			}
		}
		throw new Error(`no Overpass server answered for ${kind.kind}`);
	}
}

// A node carries its own point, a way or relation the centre Overpass gives it.
function placeOf(element: OverpassElement): NearbyPlace[] {
	const lat = element.lat ?? element.center?.lat;
	const lon = element.lon ?? element.center?.lon;
	if (lat === undefined || lon === undefined) return [];
	return [{ name: element.tags?.name ?? null, point: { lat, lon } }];
}
