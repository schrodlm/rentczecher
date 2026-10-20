/* A point on the earth, a place near a flat, and the box around flats, for
working out what lies nearest each. */
export type Point = { lat: number; lon: number };
export type NearbyPlace = { name: string | null; point: Point };
export type Box = { south: number; west: number; north: number; east: number };
export type Nearest = { place: NearbyPlace; distanceM: number };

const EARTH_RADIUS_M = 6_371_000;

/* The straight-line distance in metres. */
export function distanceM(from: Point, to: Point): number {
	const toRadians = (degrees: number) => (degrees * Math.PI) / 180;
	const dLat = toRadians(to.lat - from.lat);
	const dLon = toRadians(to.lon - from.lon);
	const a =
		Math.sin(dLat / 2) ** 2 + Math.cos(toRadians(from.lat)) * Math.cos(toRadians(to.lat)) * Math.sin(dLon / 2) ** 2;
	return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(a));
}

export function nearest(point: Point, places: readonly NearbyPlace[]): Nearest | null {
	let best: Nearest | null = null;
	for (const place of places) {
		const distance = distanceM(point, place.point);
		if (best === null || distance < best.distanceM) best = { place, distanceM: distance };
	}
	return best;
}

/* The box around the points, grown by marginM on every side so a flat at
its edge still finds what lies just outside. */
export function boxAround(points: readonly Point[], marginM: number): Box | null {
	if (points.length === 0) return null;
	const lats = points.map((point) => point.lat);
	const lons = points.map((point) => point.lon);
	const latMargin = (marginM / EARTH_RADIUS_M) * (180 / Math.PI);
	const middleLat = (Math.min(...lats) + Math.max(...lats)) / 2;
	const lonMargin = latMargin / Math.cos((middleLat * Math.PI) / 180);
	return {
		south: Math.min(...lats) - latMargin,
		west: Math.min(...lons) - lonMargin,
		north: Math.max(...lats) + latMargin,
		east: Math.max(...lons) + lonMargin
	};
}
