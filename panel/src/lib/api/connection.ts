import { invoke } from '@tauri-apps/api/core';

export type SidecarConnection = { baseUrl: string; token: string };

/* Where the sidecar listens and the token it expects. The shell spawned the
sidecar and holds both, and its sidecar_connection command replies in exactly
this shape. */
export async function sidecarConnection(): Promise<SidecarConnection> {
	return invoke<SidecarConnection>('sidecar_connection');
}
