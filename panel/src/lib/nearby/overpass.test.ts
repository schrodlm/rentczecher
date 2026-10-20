import { describe, expect, test, vi } from 'vitest';
import { NEARBY_KINDS } from './kinds';
import { OverpassClient } from './overpass';

const METRO = NEARBY_KINDS.find((kind) => kind.kind === 'metro')!;
const BOX = { south: 50.09, west: 14.42, north: 50.11, east: 14.46 };
const ANSWER = {
	elements: [
		{ type: 'node', lat: 50.1002, lon: 14.4385, tags: { name: 'Vltavská' } },
		{ type: 'way', center: { lat: 50.0902, lon: 14.4393 }, tags: { name: 'Florenc' } },
		{ type: 'node', lat: 50.1, lon: 14.44 },
		{ type: 'relation', tags: { name: 'Without a point' } }
	]
};

function json(body: unknown, status = 200): Response {
	return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('OverpassClient', () => {
	test('asks for the kind inside the box and reads back each place with a point', async () => {
		const fetchFn = vi.fn(async () => json(ANSWER));
		const places = await new OverpassClient(fetchFn).places(METRO, BOX);

		const [server, init] = fetchFn.mock.calls[0] as unknown as [string, RequestInit];
		expect(server).toBe('https://overpass-api.de/api/interpreter');
		const query = new URLSearchParams(init.body as URLSearchParams).get('data');
		expect(query).toContain('nwr["railway"="station"]["station"="subway"](50.09,14.42,50.11,14.46)');
		expect(places).toEqual([
			{ name: 'Vltavská', point: { lat: 50.1002, lon: 14.4385 } },
			{ name: 'Florenc', point: { lat: 50.0902, lon: 14.4393 } },
			{ name: null, point: { lat: 50.1, lon: 14.44 } }
		]);
	});

	test('gives up on a server that has not started answering within a few seconds', async () => {
		vi.useFakeTimers();
		try {
			const fetchFn = vi.fn(
				(server: string, init: RequestInit) =>
					new Promise<Response>((resolve, reject) => {
						if (!server.includes('overpass-api.de')) resolve(json(ANSWER));
						init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
					})
			);
			const asking = new OverpassClient(fetchFn as unknown as typeof fetch).places(METRO, BOX);
			await vi.advanceTimersByTimeAsync(6000);
			expect(await asking).toHaveLength(3);
			expect(fetchFn).toHaveBeenCalledTimes(2);
		} finally {
			vi.useRealTimers();
		}
	});

	test('asks the third server when the first two are busy or slow', async () => {
		const fetchFn = vi.fn(async (server: string) => {
			if (server.includes('overpass-api.de')) return json({}, 504);
			if (server.includes('private.coffee')) throw new DOMException('timed out', 'TimeoutError');
			return json(ANSWER);
		});
		const places = await new OverpassClient(fetchFn as unknown as typeof fetch).places(METRO, BOX);
		expect(fetchFn).toHaveBeenCalledTimes(3);
		expect(fetchFn.mock.calls[2][0]).toBe('https://overpass.kumi.systems/api/interpreter');
		expect(places).toHaveLength(3);
	});

	test('asks the second server when the first is busy', async () => {
		const fetchFn = vi.fn(async (server: string) =>
			server.includes('overpass-api.de') ? json({}, 504) : json(ANSWER)
		);
		const places = await new OverpassClient(fetchFn as unknown as typeof fetch).places(METRO, BOX);
		expect(fetchFn).toHaveBeenCalledTimes(2);
		expect(places).toHaveLength(3);
	});

	test('throws when no server answers', async () => {
		const fetchFn = vi.fn(async () => {
			throw new TypeError('offline');
		});
		await expect(new OverpassClient(fetchFn).places(METRO, BOX)).rejects.toThrow('no Overpass server answered');
	});
});
