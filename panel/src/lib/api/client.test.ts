import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { SidecarClient, type NewProfileBody, type ProfileUpdateBody } from './client';

const BASE_URL = 'http://127.0.0.1:8765';
const TOKEN = 'secret';

const PREFERENCES: NewProfileBody['preferences'] = {
	price_per_m2_weight: 0,
	disposition_weight: 0,
	preferred_dispositions: [],
	size_weight: 0,
	ideal_size_m2: null,
	place_weight: 0,
	preferred_places: [],
	land_weight: 0,
	ideal_land_m2: null,
	price_weight: 0,
	max_good_price: null
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
