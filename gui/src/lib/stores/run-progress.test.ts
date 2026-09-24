import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest';
import { RunProgressStore } from './run-progress.svelte';

/* jsdom has no EventSource. This fake lets a test dispatch named SSE
events directly, mirroring the addEventListener(kind, handler) shape
RunProgressStore actually subscribes to. */
class FakeEventSource {
	static instances: FakeEventSource[] = [];
	listeners = new Map<string, ((event: MessageEvent<string>) => void)[]>();
	closed = false;

	constructor(public url: string) {
		FakeEventSource.instances.push(this);
	}

	addEventListener(kind: string, handler: (event: MessageEvent<string>) => void) {
		const existing = this.listeners.get(kind) ?? [];
		existing.push(handler);
		this.listeners.set(kind, existing);
	}

	close() {
		this.closed = true;
	}

	emit(kind: string, data: unknown) {
		for (const handler of this.listeners.get(kind) ?? []) {
			handler({ data: JSON.stringify(data) } as MessageEvent<string>);
		}
	}
}

describe('RunProgressStore', () => {
	beforeEach(() => {
		FakeEventSource.instances = [];
		vi.stubGlobal('EventSource', FakeEventSource);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	test('moves through running to done for the watched profile', () => {
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty');
		const source = FakeEventSource.instances[0];

		source.emit('run_started', { run_id: 'r1', profile_id: 'praha7-byty' });
		expect(store.state).toEqual({ status: 'running', profileId: 'praha7-byty', scrapersDone: [] });

		source.emit('run_finished', {
			run_id: 'r1',
			profile_id: 'praha7-byty',
			status: 'ok',
			counts: { total: 1, new: 1, price_drops: 0, disappeared: 0 }
		});
		expect(store.state.status).toBe('done');
		expect(store.lastFinishedAt).toBeInstanceOf(Date);
	});

	test('ignores events for a different profile', () => {
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty');
		const source = FakeEventSource.instances[0];

		source.emit('run_started', { run_id: 'r1', profile_id: 'domazlice-domy' });
		expect(store.state).toEqual({ status: 'idle' });
	});

	test('reports the failed status distinctly, carrying the error message', () => {
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty');
		const source = FakeEventSource.instances[0];

		source.emit('run_finished', {
			run_id: 'r1',
			profile_id: 'praha7-byty',
			status: 'failed',
			error: 'scraper exploded'
		});
		expect(store.state).toEqual({
			status: 'failed',
			profileId: 'praha7-byty',
			error: 'scraper exploded'
		});
	});

	test('reports the failed status when the pipeline itself fails with counts and no error', () => {
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty');
		const source = FakeEventSource.instances[0];

		source.emit('run_finished', {
			run_id: 'r1',
			profile_id: 'praha7-byty',
			status: 'failed',
			counts: { total: 3, new: 1, price_drops: 0, disappeared: 0 }
		});
		expect(store.state).toEqual({
			status: 'failed',
			profileId: 'praha7-byty',
			error: null
		});
	});

	test('calls onfinished only for a completed run of the watched profile', () => {
		const onfinished = vi.fn();
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty', onfinished);
		const source = FakeEventSource.instances[0];

		source.emit('run_finished', {
			run_id: 'r1',
			profile_id: 'domazlice-domy',
			status: 'ok',
			counts: { total: 0, new: 0, price_drops: 0, disappeared: 0 }
		});
		expect(onfinished).not.toHaveBeenCalled();

		source.emit('run_finished', {
			run_id: 'r2',
			profile_id: 'praha7-byty',
			status: 'ok',
			counts: { total: 0, new: 0, price_drops: 0, disappeared: 0 }
		});
		expect(onfinished).toHaveBeenCalledOnce();
	});

	test('closes the previous connection when connecting again', () => {
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty');
		const first = FakeEventSource.instances[0];

		store.connect('http://x/events', 'domazlice-domy');

		expect(first.closed).toBe(true);
	});
});
