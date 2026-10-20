import { beforeEach, describe, expect, test, vi } from 'vitest';
import type { Box, NearbyPlace } from './geometry';
import type { NearbyKindShown } from './kinds';
import { NearbyStore } from './nearby-store.svelte';

const FLAT = { lat: 50.1, lon: 14.44 };
const VLTAVSKA: NearbyPlace = { name: 'Vltavská', point: { lat: 50.1002, lon: 14.4385 } };

class FakeOverpass {
	asked: { kind: string; box: Box }[] = [];
	answers: ((places: NearbyPlace[]) => void)[] = [];
	failing = false;

	places(kind: NearbyKindShown, box: Box): Promise<NearbyPlace[]> {
		this.asked.push({ kind: kind.kind, box });
		if (this.failing) return Promise.reject(new Error('busy'));
		return new Promise((resolve) => this.answers.push(resolve));
	}
}

beforeEach(() => {
	localStorage.clear();
});

describe('NearbyStore', () => {
	test('asks for a kind switched on and finds the nearest of it', async () => {
		const overpass = new FakeOverpass();
		const store = new NearbyStore(overpass);
		store.show('p1', [FLAT]);
		store.toggle('metro');
		overpass.answers[0]([VLTAVSKA]);
		await vi.waitFor(() => expect(store.nearestTo(FLAT, 'metro')?.place.name).toBe('Vltavská'));
	});

	test("keeps a profile's kinds on this machine, in the list's order", () => {
		const first = new NearbyStore(new FakeOverpass());
		first.show('p1', [FLAT]);
		first.toggle('park');
		first.toggle('metro');
		const again = new NearbyStore(new FakeOverpass());
		again.show('p1', [FLAT]);
		expect(again.chosen).toEqual(['metro', 'park']);
	});

	test('asks only once for an area it already has', () => {
		const overpass = new FakeOverpass();
		const store = new NearbyStore(overpass);
		store.show('p1', [FLAT]);
		store.toggle('metro');
		store.show('p1', [FLAT]);
		expect(overpass.asked).toHaveLength(1);
	});

	test('drops an answer that arrives after another profile is shown', async () => {
		const overpass = new FakeOverpass();
		const store = new NearbyStore(overpass);
		store.show('p1', [FLAT]);
		store.toggle('metro');
		store.show('p2', [FLAT]);
		overpass.answers[0]([VLTAVSKA]);
		await Promise.resolve();
		expect(store.nearestTo(FLAT, 'metro')).toBeNull();
	});

	test('shows nothing of a kind whose servers are busy', async () => {
		const overpass = new FakeOverpass();
		overpass.failing = true;
		const store = new NearbyStore(overpass);
		store.show('p1', [FLAT]);
		store.toggle('metro');
		await Promise.resolve();
		expect(store.nearestTo(FLAT, 'metro')).toBeNull();
	});

	test('switches a kind back off', () => {
		const store = new NearbyStore(new FakeOverpass());
		store.show('p1', [FLAT]);
		store.toggle('metro');
		store.toggle('metro');
		expect(store.chosen).toEqual([]);
	});

	test('gives the distances to the first kinds it has answers for', async () => {
		const overpass = new FakeOverpass();
		const store = new NearbyStore(overpass);
		store.show('p1', [FLAT]);
		store.toggle('metro');
		store.toggle('tram');
		store.toggle('park');
		overpass.answers[0]([VLTAVSKA]);
		overpass.answers[2]([VLTAVSKA]);
		await vi.waitFor(() => expect(store.distancesFrom(FLAT, 2).map((each) => each.kind)).toEqual(['metro']));
	});

	test('loads a kind for a profile shown while the last one was still asking for it', async () => {
		const overpass = new FakeOverpass();
		const store = new NearbyStore(overpass);
		store.show('p1', [FLAT]);
		store.toggle('metro');
		store.show('p2', [FLAT]);
		store.toggle('metro');
		expect(overpass.asked).toHaveLength(2);
		overpass.answers[1]([VLTAVSKA]);
		await vi.waitFor(() => expect(store.nearestTo(FLAT, 'metro')?.place.name).toBe('Vltavská'));
	});

	test('asks again once an answer comes when the flats spread meanwhile', async () => {
		const overpass = new FakeOverpass();
		const store = new NearbyStore(overpass);
		store.show('p1', [FLAT]);
		store.toggle('metro');
		store.show('p1', [FLAT, { lat: 49.2, lon: 16.6 }]);
		overpass.answers[0]([VLTAVSKA]);
		await vi.waitFor(() => expect(overpass.asked).toHaveLength(2));
	});

	test('asks again a minute after no server answered', async () => {
		vi.useFakeTimers();
		try {
			const overpass = new FakeOverpass();
			overpass.failing = true;
			const store = new NearbyStore(overpass);
			store.show('p1', [FLAT]);
			store.toggle('metro');
			await vi.advanceTimersByTimeAsync(60_000);
			expect(overpass.asked).toHaveLength(2);
		} finally {
			vi.useRealTimers();
		}
	});
});
