import { invoke } from '@tauri-apps/api/core';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { sidecarConnection } from './connection';

vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

describe('sidecarConnection', () => {
	afterEach(() => {
		vi.mocked(invoke).mockReset();
	});

	test("returns the shell's answer to sidecar_connection", async () => {
		vi.mocked(invoke).mockResolvedValue({ baseUrl: 'http://127.0.0.1:41000', token: 'abc' });
		await expect(sidecarConnection()).resolves.toEqual({
			baseUrl: 'http://127.0.0.1:41000',
			token: 'abc'
		});
		expect(invoke).toHaveBeenCalledExactlyOnceWith('sidecar_connection');
	});

	test('propagates a failed ask so the page can show its error', async () => {
		vi.mocked(invoke).mockRejectedValue(new Error('no shell'));
		await expect(sidecarConnection()).rejects.toThrow('no shell');
	});
});
