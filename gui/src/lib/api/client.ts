import type { paths } from './types.gen';

type ProfileListResponse =
	paths['/v1/profiles']['get']['responses']['200']['content']['application/json'];

/* Talks to the sidecar's loopback API. The base URL and token are
constructor inputs on purpose: the page constructing a client owns where
they come from. In dev they are read from gui/.env, which Vite exposes to
page code through its PUBLIC_ env var convention. */
export class SidecarClient {
	constructor(
		private readonly baseUrl: string,
		private readonly token: string
	) {}

	async listProfiles(): Promise<ProfileListResponse> {
		const response = await fetch(`${this.baseUrl}/v1/profiles`, {
			headers: { Authorization: `Bearer ${this.token}` }
		});
		if (!response.ok) {
			throw new Error(`GET /v1/profiles failed: ${response.status} ${response.statusText}`);
		}
		return response.json();
	}
}
