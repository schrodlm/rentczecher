import createClient from 'openapi-fetch';
import type { components, paths } from './types.gen';

export type ProfileModel = components['schemas']['ProfileModel'];
export type ListingModel = components['schemas']['ListingModel'];
export type PortalHealthModel = components['schemas']['PortalHealthModel'];
export type RunTriggeredModel = components['schemas']['RunTriggeredModel'];
type ListingFilter = NonNullable<
	paths['/v1/profiles/{profile_id}/listings']['get']['parameters']['query']
>['filter'];

/* Talks to the sidecar's loopback API through openapi-fetch, so every
path, parameter, and body below is compile-checked against the generated
contract (ADR 2). The base URL and token are constructor inputs on
purpose: the page constructing a client owns where they come from. In dev
they are read from gui/.env, which Vite exposes to page code through its
PUBLIC_ env var convention. */
export class SidecarClient {
	private readonly api: ReturnType<typeof createClient<paths>>;

	constructor(
		private readonly baseUrl: string,
		private readonly token: string
	) {
		this.api = createClient<paths>({
			baseUrl,
			headers: { Authorization: `Bearer ${token}` }
		});
	}

	async listProfiles(): Promise<ProfileModel[]> {
		const { data, response } = await this.api.GET('/v1/profiles');
		return this.require(data, response);
	}

	async listListings(profileId: string, filter: ListingFilter = 'new'): Promise<ListingModel[]> {
		const { data, response } = await this.api.GET('/v1/profiles/{profile_id}/listings', {
			params: { path: { profile_id: profileId }, query: { filter } }
		});
		return this.require(data, response);
	}

	async markViewed(profileId: string, listingId: string): Promise<void> {
		const { response } = await this.api.PATCH(
			'/v1/profiles/{profile_id}/listings/{listing_id}/viewed',
			{ params: { path: { profile_id: profileId, listing_id: listingId } } }
		);
		if (!response.ok) {
			throw new Error(`${response.url} failed: ${response.status} ${response.statusText}`);
		}
	}

	async health(): Promise<PortalHealthModel[]> {
		const { data, response } = await this.api.GET('/v1/health');
		return this.require(data, response);
	}

	async triggerRun(profileId: string): Promise<RunTriggeredModel> {
		const { data, response } = await this.api.POST('/v1/runs', {
			body: { profile_id: profileId }
		});
		return this.require(data, response);
	}

	/* openapi-fetch reports failure as a value, this facade keeps the
	throw-based contract its callers are built against. */
	private require<T>(data: T | undefined, response: Response): T {
		if (data === undefined) {
			throw new Error(`${response.url} failed: ${response.status} ${response.statusText}`);
		}
		return data;
	}

	/* EventSource cannot set an Authorization header, so the token rides
	the query string here only - the one documented exception the sidecar's
	auth layer carves out for this route. */
	eventsUrl(): string {
		return `${this.baseUrl}/v1/events?token=${encodeURIComponent(this.token)}`;
	}
}
