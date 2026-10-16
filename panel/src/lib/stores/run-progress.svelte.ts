import type { RunFinishedEvent, RunProgressEvent, RunStartedEvent } from '$lib/api/events';

export type RunState =
	| { status: 'idle' }
	| { status: 'running'; scrapersDone: RunProgressEvent[] }
	| { status: 'done'; brokenPortals: string[] }
	| { status: 'failed'; error: string | null; noPortalAnswered: boolean };

/* Tracks one profile's run lifecycle from the SSE stream and exposes the
timestamp of the last completed run - the closest truthful stand-in for
"last run info" the v0 contract offers, since no run-history endpoint
exists yet. Only events for the watched profile move the state; a run
triggered for a different profile is ignored. */
export class RunProgressStore {
	state = $state<RunState>({ status: 'idle' });
	lastFinishedAt = $state<Date | null>(null);
	private source: EventSource | null = null;

	connect(eventsUrl: string, profileId: string, onfinished?: () => void): void {
		this.disconnect();
		this.source = new EventSource(eventsUrl);

		this.source.addEventListener('run_started', (event: MessageEvent<string>) => {
			const data: RunStartedEvent = JSON.parse(event.data);
			if (data.profile_id !== profileId) return;
			this.state = { status: 'running', scrapersDone: [] };
		});

		this.source.addEventListener('run_progress', (event: MessageEvent<string>) => {
			const data: RunProgressEvent = JSON.parse(event.data);
			if (data.profile_id !== profileId || this.state.status !== 'running') return;
			this.state = { ...this.state, scrapersDone: [...this.state.scrapersDone, data] };
		});

		this.source.addEventListener('run_finished', (event: MessageEvent<string>) => {
			const data: RunFinishedEvent = JSON.parse(event.data);
			if (data.profile_id !== profileId) return;
			const scrapersDone = this.state.status === 'running' ? this.state.scrapersDone : [];
			const brokenPortals = scrapersDone
				.filter((done) => done.status === 'broken')
				.map((done) => done.scraper);
			if (data.error !== null && data.error !== undefined) {
				this.state = { status: 'failed', error: data.error, noPortalAnswered: false };
			} else if (data.status === 'failed') {
				const noPortalAnswered =
					scrapersDone.length > 0 && brokenPortals.length === scrapersDone.length;
				this.state = { status: 'failed', error: null, noPortalAnswered };
			} else {
				this.lastFinishedAt = new Date();
				this.state = { status: 'done', brokenPortals };
			}
			onfinished?.();
		});
	}

	disconnect(): void {
		this.source?.close();
		this.source = null;
	}
}
