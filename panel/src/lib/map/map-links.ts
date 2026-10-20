import type { components } from '$lib/api/types.gen';

type PointModel = components['schemas']['PointModel'];

const STREET_ZOOM = 17;

/* The point on Mapy.cz, pinned, in the form its documented URL API takes:
the centre as longitude, then latitude. */
export function mapyUrl(point: PointModel): string {
	return `https://mapy.com/fnc/v1/showmap?mapset=basic&center=${point.lon},${point.lat}&zoom=${STREET_ZOOM}&marker=true`;
}

/* The point on Google Maps, in its documented search URL. */
export function googleMapsUrl(point: PointModel): string {
	return `https://www.google.com/maps/search/?api=1&query=${point.lat},${point.lon}`;
}
