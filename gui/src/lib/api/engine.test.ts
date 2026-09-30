import { listen } from '@tauri-apps/api/event';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { onEngineStopped } from './engine';

vi.mock('@tauri-apps/api/event', () => ({ listen: vi.fn() }));

describe('onEngineStopped', () => {
	afterEach(() => {
		vi.mocked(listen).mockReset();
	});

	test("listens for the shell's engine-stopped event and calls back on it", async () => {
		vi.mocked(listen).mockResolvedValue(() => {});
		const onstopped = vi.fn();

		await onEngineStopped(onstopped);

		expect(listen).toHaveBeenCalledOnce();
		const [eventName, handler] = vi.mocked(listen).mock.calls[0];
		expect(eventName).toBe('engine-stopped');
		handler({ event: 'engine-stopped', id: 1, payload: null });
		expect(onstopped).toHaveBeenCalledOnce();
	});
});
