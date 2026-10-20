/* jsdom has no EventSource. This fake lets a test dispatch named SSE
events directly, mirroring the addEventListener(kind, handler) shape
the stores subscribe with. */
export class FakeEventSource {
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
