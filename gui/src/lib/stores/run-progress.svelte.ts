import type { RunFinishedEvent, RunProgressEvent, RunStartedEvent } from '$lib/api/events';

export type RunState =
	| { status: 'idle' }
	| { status: 'running'; profileId: string; scrapersDone: RunProgressEvent[] }
	| { status: 'done'; profileId: string; finishedAt: Date }
	| { status: 'failed'; profileId: string; error: string | null };

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
			this.state = { status: 'running', profileId, scrapersDone: [] };
		});

		this.source.addEventListener('run_progress', (event: MessageEvent<string>) => {
			const data: RunProgressEvent = JSON.parse(event.data);
			if (data.profile_id !== profileId || this.state.status !== 'running') return;
			this.state = { ...this.state, scrapersDone: [...this.state.scrapersDone, data] };
		});

		this.source.addEventListener('run_finished', (event: MessageEvent<string>) => {
			const data: RunFinishedEvent = JSON.parse(event.data);
			if (data.profile_id !== profileId) return;
			if (data.error !== null && data.error !== undefined) {
				this.state = { status: 'failed', profileId, error: data.error };
				return;
			}
			if (data.status === 'failed') {
				this.state = { status: 'failed', profileId, error: null };
				return;
			}
			const finishedAt = new Date();
			this.lastFinishedAt = finishedAt;
			this.state = { status: 'done', profileId, finishedAt };
			onfinished?.();
		});
	}

	disconnect(): void {
		this.source?.close();
		this.source = null;
	}
}
