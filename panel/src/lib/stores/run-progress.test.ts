import { describe, expect, test, vi, beforeEach, afterEach } from 'vitest';
import { FakeEventSource } from '$lib/test-support/fake-event-source';
import { RunProgressStore } from './run-progress.svelte';

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
		expect(store.state).toEqual({ status: 'running', scrapersDone: [] });

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
			error: 'scraper exploded',
			noPortalAnswered: false
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
			error: null,
			noPortalAnswered: false
		});
	});

	test('reports that no portal answered when every portal of a failed run broke', () => {
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty');
		const source = FakeEventSource.instances[0];

		source.emit('run_started', { run_id: 'r1', profile_id: 'praha7-byty' });
		for (const scraper of ['sreality', 'bezrealitky']) {
			source.emit('run_progress', {
				run_id: 'r1',
				profile_id: 'praha7-byty',
				scraper,
				status: 'broken',
				listing_count: 0
			});
		}
		source.emit('run_finished', {
			run_id: 'r1',
			profile_id: 'praha7-byty',
			status: 'failed',
			counts: { total: 0, new: 0, price_drops: 0, disappeared: 0 }
		});
		expect(store.state).toEqual({ status: 'failed', error: null, noPortalAnswered: true });
	});

	test('lists the portals that broke in a run that otherwise completed', () => {
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty');
		const source = FakeEventSource.instances[0];

		source.emit('run_started', { run_id: 'r1', profile_id: 'praha7-byty' });
		source.emit('run_progress', {
			run_id: 'r1',
			profile_id: 'praha7-byty',
			scraper: 'sreality',
			status: 'ok',
			listing_count: 4
		});
		source.emit('run_progress', {
			run_id: 'r1',
			profile_id: 'praha7-byty',
			scraper: 'remax',
			status: 'broken',
			listing_count: 0
		});
		source.emit('run_finished', {
			run_id: 'r1',
			profile_id: 'praha7-byty',
			status: 'partial',
			counts: { total: 4, new: 0, price_drops: 0, disappeared: 0 }
		});
		expect(store.state).toEqual({ status: 'done', brokenPortals: ['remax'] });
	});

	test('calls onfinished for every finished run of the watched profile, failed ones too', () => {
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

		source.emit('run_finished', {
			run_id: 'r3',
			profile_id: 'praha7-byty',
			status: 'failed',
			counts: { total: 0, new: 0, price_drops: 0, disappeared: 0 }
		});
		expect(onfinished).toHaveBeenCalledTimes(2);
	});

	test('closes the previous connection when connecting again', () => {
		const store = new RunProgressStore();
		store.connect('http://x/events', 'praha7-byty');
		const first = FakeEventSource.instances[0];

		store.connect('http://x/events', 'domazlice-domy');

		expect(first.closed).toBe(true);
	});
});
