import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import {
	ApiError,
	SidecarClient,
	type GalleryModel,
	type NewProfileBody,
	type PostingPricesModel,
	type ProfileUpdateBody
} from './client';
import { trackedProperty } from '$lib/test-support/tracked-property';

const BASE_URL = 'http://127.0.0.1:8765';
const TOKEN = 'secret';

const PREFERENCES: NewProfileBody['preferences'] = {
	price_per_m2_weight: 0,
	disposition_weight: 0,
	preferred_dispositions: [],
	size_weight: 0,
	preferred_size_m2: null,
	place_weight: 0,
	preferred_places: [],
	land_weight: 0,
	preferred_land_m2: null,
	price_weight: 0,
	preferred_price: null
};

const NEW_PROFILE: NewProfileBody = {
	name: 'Praha 7 byty',
	portals: ['sreality'],
	criteria: {
		offer_type: 'rent',
		estate_type: 'flat',
		place: { kind: 'obvod', code: 78 },
		min_price: null,
		max_price: 25000,
		min_size_m2: null,
		max_size_m2: null,
		min_land_m2: null,
		dispositions: ['2+kk']
	},
	preferences: PREFERENCES
};

const UPDATE: ProfileUpdateBody = { name: 'Byty', paused: true, portals: ['remax'], preferences: PREFERENCES };

let requests: Request[];

function answerWith(status: number, body?: unknown): void {
	vi.stubGlobal(
		'fetch',
		vi.fn(async (request: Request) => {
			requests.push(request);
			return new Response(body === undefined ? null : JSON.stringify(body), {
				status,
				headers: { 'Content-Type': 'application/json' }
			});
		})
	);
}

beforeEach(() => {
	requests = [];
});

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('createProfile', () => {
	test('posts the new profile with the token and returns the stored one', async () => {
		answerWith(201, { id: 'p1', name: 'Praha 7 byty' });
		const created = await new SidecarClient(BASE_URL, TOKEN).createProfile(NEW_PROFILE);

		const [request] = requests;
		expect(request.method).toBe('POST');
		expect(request.url).toBe(`${BASE_URL}/v1/profiles`);
		expect(request.headers.get('Authorization')).toBe(`Bearer ${TOKEN}`);
		expect(await request.json()).toEqual(NEW_PROFILE);
		expect(created).toEqual({ id: 'p1', name: 'Praha 7 byty' });
	});

	test('throws when the engine refuses the profile', async () => {
		answerWith(422, { detail: 'min_price must not exceed max_price' });
		await expect(new SidecarClient(BASE_URL, TOKEN).createProfile(NEW_PROFILE)).rejects.toThrow('422');
	});

	test('keeps the reason the engine gave for refusing', async () => {
		answerWith(422, { detail: 'min_price must not exceed max_price' });
		await expect(new SidecarClient(BASE_URL, TOKEN).createProfile(NEW_PROFILE)).rejects.toMatchObject({
			status: 422,
			reason: 'min_price must not exceed max_price'
		});
	});

	test('keeps no reason when the engine gave none in words', async () => {
		answerWith(422, { detail: [{ loc: ['body', 'name'], msg: 'Field required', type: 'missing' }] });
		const refusal = new SidecarClient(BASE_URL, TOKEN).createProfile(NEW_PROFILE);
		await expect(refusal).rejects.toBeInstanceOf(ApiError);
		await expect(refusal).rejects.toMatchObject({ status: 422, reason: null });
	});
});

describe('updateProfile', () => {
	test('puts the changes to the profile and returns it as saved', async () => {
		answerWith(200, { id: 'p1', name: 'Byty' });
		const updated = await new SidecarClient(BASE_URL, TOKEN).updateProfile('p1', UPDATE);

		const [request] = requests;
		expect(request.method).toBe('PUT');
		expect(request.url).toBe(`${BASE_URL}/v1/profiles/p1`);
		expect(await request.json()).toEqual(UPDATE);
		expect(updated).toEqual({ id: 'p1', name: 'Byty' });
	});

	test('throws for an unknown profile', async () => {
		answerWith(404, { detail: "unknown profile 'p1'" });
		await expect(new SidecarClient(BASE_URL, TOKEN).updateProfile('p1', UPDATE)).rejects.toThrow('404');
	});
});

describe('deleteProfile', () => {
	test('deletes the profile', async () => {
		answerWith(204);
		await new SidecarClient(BASE_URL, TOKEN).deleteProfile('p1');

		const [request] = requests;
		expect(request.method).toBe('DELETE');
		expect(request.url).toBe(`${BASE_URL}/v1/profiles/p1`);
	});

	test('throws for an unknown profile', async () => {
		answerWith(404, { detail: "unknown profile 'p1'" });
		await expect(new SidecarClient(BASE_URL, TOKEN).deleteProfile('p1')).rejects.toThrow('404');
	});
});

describe('markFavourite', () => {
	test('puts the flat among the profile\'s favourites', async () => {
		answerWith(204);
		await new SidecarClient(BASE_URL, TOKEN).markFavourite('p1', 'prop-1');

		const [request] = requests;
		expect(request.method).toBe('PUT');
		expect(request.url).toBe(`${BASE_URL}/v1/profiles/p1/properties/prop-1/favourite`);
	});

	test('throws for an unknown profile', async () => {
		answerWith(404, { detail: "unknown profile 'p1'" });
		await expect(new SidecarClient(BASE_URL, TOKEN).markFavourite('p1', 'prop-1')).rejects.toThrow('404');
	});
});

describe('clearFavourite', () => {
	test('takes the flat out of the profile\'s favourites', async () => {
		answerWith(204);
		await new SidecarClient(BASE_URL, TOKEN).clearFavourite('p1', 'prop-1');

		const [request] = requests;
		expect(request.method).toBe('DELETE');
		expect(request.url).toBe(`${BASE_URL}/v1/profiles/p1/properties/prop-1/favourite`);
	});
});

describe('priceHistory', () => {
	test("gets the prices of every posting of the flat", async () => {
		const postings: PostingPricesModel[] = [
			{
				listing_id: 'sreality:1',
				source: 'sreality',
				url: 'https://sreality.cz/detail/1',
				changes: [{ price: 20000, charges: null, first_seen_at: '2026-10-01', last_seen_at: '2026-10-03' }]
			}
		];
		answerWith(200, postings);
		const answered = await new SidecarClient(BASE_URL, TOKEN).priceHistory('p1', 'prop-1');

		const [request] = requests;
		expect(request.method).toBe('GET');
		expect(request.url).toBe(`${BASE_URL}/v1/profiles/p1/properties/prop-1/price-history`);
		expect(answered).toEqual(postings);
	});

	test('throws for a flat the profile does not track', async () => {
		answerWith(404, { detail: 'profile p1 does not track property prop-1' });
		await expect(new SidecarClient(BASE_URL, TOKEN).priceHistory('p1', 'prop-1')).rejects.toThrow('404');
	});
});

describe('listTrackedProperties', () => {
	test('gets the tracked flats with links to the engine for their main photos', async () => {
		answerWith(200, [
			trackedProperty('prop-1', { main_photo: { url: '/v1/photos/a.jpg?sig=s' } }),
			trackedProperty('prop-2', { main_photo: null })
		]);
		const answered = await new SidecarClient(BASE_URL, TOKEN).listTrackedProperties('p1', 'all');

		const [request] = requests;
		expect(request.url).toBe(`${BASE_URL}/v1/profiles/p1/properties?filter=all`);
		expect(answered.map((tracked) => tracked.main_photo)).toEqual([
			{ url: `${BASE_URL}/v1/photos/a.jpg?sig=s` },
			null
		]);
	});
});

describe('gallery', () => {
	test('gets the flat\'s stored photos with links to the engine', async () => {
		const gallery: GalleryModel = {
			status: 'stored',
			source: 'sreality',
			posting_url: 'https://sreality.cz/detail/1',
			photo_count: 3,
			photos: [{ url: '/v1/photos/a.jpg?sig=s' }]
		};
		answerWith(200, gallery);
		const answered = await new SidecarClient(BASE_URL, TOKEN).gallery('p1', 'prop-1');

		const [request] = requests;
		expect(request.method).toBe('GET');
		expect(request.url).toBe(`${BASE_URL}/v1/profiles/p1/properties/prop-1/gallery`);
		expect(answered).toEqual({ ...gallery, photos: [{ url: `${BASE_URL}/v1/photos/a.jpg?sig=s` }] });
	});

	test('throws for a flat the profile does not track', async () => {
		answerWith(404, { detail: 'profile p1 does not track property prop-1' });
		await expect(new SidecarClient(BASE_URL, TOKEN).gallery('p1', 'prop-1')).rejects.toThrow('404');
	});
});

describe('requestGallery', () => {
	test('asks for the flat\'s whole gallery', async () => {
		answerWith(204);
		await new SidecarClient(BASE_URL, TOKEN).requestGallery('p1', 'prop-1');

		const [request] = requests;
		expect(request.method).toBe('PUT');
		expect(request.url).toBe(`${BASE_URL}/v1/profiles/p1/properties/prop-1/gallery-request`);
	});

	test('throws for a flat the profile does not track', async () => {
		answerWith(404, { detail: 'profile p1 does not track property prop-1' });
		await expect(new SidecarClient(BASE_URL, TOKEN).requestGallery('p1', 'prop-1')).rejects.toThrow('404');
	});
});

describe('searchPlaces', () => {
	const HOLESOVICE = { kind: 'cast_obce', code: 490067, name: 'Holešovice', obec: 'Praha', okres: null };

	test('asks for places starting with the query and returns them', async () => {
		answerWith(200, [HOLESOVICE]);
		const places = await new SidecarClient(BASE_URL, TOKEN).searchPlaces('holeš');

		const url = new URL(requests[0].url);
		expect(url.pathname).toBe('/v1/places');
		expect([...url.searchParams]).toEqual([['q', 'holeš']]);
		expect(places).toEqual([HOLESOVICE]);
	});

	test('sends the place to search inside as kind and code, and each kind', async () => {
		answerWith(200, []);
		await new SidecarClient(BASE_URL, TOKEN).searchPlaces('ho', { kind: 'obvod', code: 78 }, ['cast_obce', 'ulice']);

		const url = new URL(requests[0].url);
		expect(url.searchParams.get('within')).toBe('obvod:78');
		expect(url.searchParams.getAll('kind')).toEqual(['cast_obce', 'ulice']);
	});

	test('throws when the engine refuses the search', async () => {
		answerWith(422, { detail: "unknown place 'obvod 7'" });
		await expect(
			new SidecarClient(BASE_URL, TOKEN).searchPlaces('ho', { kind: 'obvod', code: 7 })
		).rejects.toThrow('422');
	});
});
