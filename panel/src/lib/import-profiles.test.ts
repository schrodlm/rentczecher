import { afterEach, describe, expect, test } from 'vitest';
import { ApiError, type NewProfileBody, type ProfileModel } from '$lib/api/client';
import { importProfiles, importProfilesFile } from '$lib/import-profiles';
import { keptNearbyKinds } from '$lib/nearby/kept-kinds';
import { newProfileBodyOf, type ProfileInFile } from '$lib/profiles-file';
import { storedProfile } from '$lib/test-support/stored-profile';

/* Creates each profile under the next id, and refuses one named in refusing. */
function engine(refusing: string[] = []) {
	const bodies: NewProfileBody[] = [];
	return {
		bodies,
		async createProfile(body: NewProfileBody): Promise<ProfileModel> {
			if (refusing.includes(body.name)) {
				const response = new Response(null, { status: 422 });
				throw new ApiError(response, `place ${body.criteria.place.kind} ${body.criteria.place.code} not found`);
			}
			bodies.push(body);
			return storedProfile(`new-${bodies.length}`, body.name);
		}
	};
}

function inFile(name: string, nearbyKinds: ProfileInFile['nearbyKinds'] = []): ProfileInFile {
	return { profile: newProfileBodyOf(storedProfile('old', name)), nearbyKinds };
}

afterEach(() => localStorage.clear());

describe('importProfiles', () => {
	test('adds every profile in the file as a new one, in the file order', async () => {
		const client = engine();
		const outcome = await importProfiles(client, [inFile('Praha'), inFile('Brno')], []);
		expect(outcome.added.map((profile) => [profile.id, profile.name])).toEqual([
			['new-1', 'Praha'],
			['new-2', 'Brno']
		]);
		expect(outcome.refused).toEqual([]);
		expect(client.bodies[0]).toEqual(newProfileBodyOf(storedProfile('old', 'Praha')));
	});

	test('numbers a name already kept, or already added from the same file', async () => {
		const client = engine();
		const outcome = await importProfiles(client, [inFile('Praha'), inFile('Praha'), inFile('Brno')], ['Praha']);
		expect(outcome.added.map((profile) => profile.name)).toEqual(['Praha (2)', 'Praha (3)', 'Brno']);
	});

	test('keeps each added profile showing the nearby kinds it was exported with', async () => {
		const outcome = await importProfiles(engine(), [inFile('Praha', ['metro', 'park']), inFile('Brno')], []);
		expect(keptNearbyKinds(outcome.added[0].id)).toEqual(['metro', 'park']);
		expect(keptNearbyKinds(outcome.added[1].id)).toEqual([]);
	});

	test('gives a refused profile no number, so the next one of its name takes the name', async () => {
		let refusedOnce = false;
		const client = {
			async createProfile(body: NewProfileBody): Promise<ProfileModel> {
				if (!refusedOnce) {
					refusedOnce = true;
					throw new Error('network down');
				}
				return storedProfile('new-1', body.name);
			}
		};
		const outcome = await importProfiles(client, [inFile('Praha'), inFile('Praha')], []);
		expect(outcome.added.map((profile) => profile.name)).toEqual(['Praha']);
		expect(outcome.refused).toEqual([{ name: 'Praha', reason: 'network down' }]);
	});

	test('adds the rest when the engine refuses a profile, and reports the refused one by its name in the file', async () => {
		const outcome = await importProfiles(engine(['Praha']), [inFile('Praha'), inFile('Brno')], []);
		expect(outcome.added.map((profile) => profile.name)).toEqual(['Brno']);
		expect(outcome.refused).toEqual([{ name: 'Praha', reason: 'place obec 554782 not found' }]);
	});
});

describe('importProfilesFile', () => {
	function file(opened: ProfileInFile[] | 'unreadable' | null | Error) {
		return {
			async open() {
				if (opened instanceof Error) throw opened;
				return opened;
			}
		};
	}

	test('reports the profiles it added from the chosen file, numbering names kept when it was chosen', async () => {
		const report = await importProfilesFile(file([inFile('Praha')]), engine(), () => ['Praha']);
		expect(report?.status === 'done' && report.outcome.added.map((profile) => profile.name)).toEqual(['Praha (2)']);
	});

	test('reports nothing when the user chose no file', async () => {
		expect(await importProfilesFile(file(null), engine(), () => [])).toBeNull();
	});

	test('reports a file that is not a file of profiles, and one the shell could not read', async () => {
		expect(await importProfilesFile(file('unreadable'), engine(), () => [])).toEqual({ status: 'unreadable' });
		expect(await importProfilesFile(file(new Error('permission denied')), engine(), () => [])).toEqual({
			status: 'failed',
			reason: 'permission denied'
		});
	});
});
