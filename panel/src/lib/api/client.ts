import createClient from 'openapi-fetch';
import type { components, paths } from './types.gen';

export type ProfileModel = components['schemas']['ProfileModel'];
export type NewProfileBody = components['schemas']['NewProfileBody'];
export type ProfileUpdateBody = components['schemas']['ProfileUpdateBody'];
export type PlaceRef = components['schemas']['PlaceRefModel'];
export type NamedPlace = components['schemas']['NamedPlaceModel'];
export type ListingModel = components['schemas']['ListingModel'];
export type PortalHealthModel = components['schemas']['PortalHealthModel'];
export type RunTriggeredModel = components['schemas']['RunTriggeredModel'];
type ListingFilter = NonNullable<
	paths['/v1/profiles/{profile_id}/listings']['get']['parameters']['query']
>['filter'];

/* Talks to the sidecar's loopback API through openapi-fetch, so every
path, parameter, and body below is compile-checked against the generated
contract. The base URL and token are constructor inputs, so tests can point
a client at any fake. */
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

	async createProfile(body: NewProfileBody): Promise<ProfileModel> {
		const { data, response } = await this.api.POST('/v1/profiles', { body });
		return this.require(data, response);
	}

	async updateProfile(profileId: string, body: ProfileUpdateBody): Promise<ProfileModel> {
		const { data, response } = await this.api.PUT('/v1/profiles/{profile_id}', {
			params: { path: { profile_id: profileId } },
			body
		});
		return this.require(data, response);
	}

	async deleteProfile(profileId: string): Promise<void> {
		const { response } = await this.api.DELETE('/v1/profiles/{profile_id}', {
			params: { path: { profile_id: profileId } }
		});
		if (!response.ok) {
			throw this.httpError(response);
		}
	}

	/* Places whose official name starts with the query, broadest kind first,
	optionally only those at least partly inside one place and of some kinds. */
	async searchPlaces(query: string, within?: PlaceRef, kinds?: PlaceRef['kind'][]): Promise<NamedPlace[]> {
		const { data, response } = await this.api.GET('/v1/places', {
			params: {
				query: {
					q: query,
					within: within ? `${within.kind}:${within.code}` : undefined,
					kind: kinds
				}
			}
		});
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
			throw this.httpError(response);
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
			throw this.httpError(response);
		}
		return data;
	}

	private httpError(response: Response): Error {
		return new Error(`${response.url} failed: ${response.status} ${response.statusText}`);
	}

	/* EventSource cannot set an Authorization header, so the token rides
	the query string here only - the one documented exception the sidecar's
	auth layer carves out for this route. */
	eventsUrl(): string {
		return `${this.baseUrl}/v1/events?token=${encodeURIComponent(this.token)}`;
	}
}
