import { describe, expect, test } from 'vitest';
import { googleMapsUrl, mapyUrl } from './map-links';

const POINT = { lat: 50.1006, lon: 14.4441 };

describe('mapyUrl', () => {
	test('centres Mapy.cz on the point, longitude first, and pins it', () => {
		const url = new URL(mapyUrl(POINT));
		expect(url.origin + url.pathname).toBe('https://mapy.com/fnc/v1/showmap');
		expect(url.searchParams.get('center')).toBe('14.4441,50.1006');
		expect(url.searchParams.get('marker')).toBe('true');
	});
});

describe('googleMapsUrl', () => {
	test('searches Google Maps for the point, latitude first', () => {
		const url = new URL(googleMapsUrl(POINT));
		expect(url.origin + url.pathname).toBe('https://www.google.com/maps/search/');
		expect(url.searchParams.get('api')).toBe('1');
		expect(url.searchParams.get('query')).toBe('50.1006,14.4441');
	});
});
