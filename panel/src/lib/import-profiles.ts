import { ApiError, type ProfileModel, type SidecarClient } from '$lib/api/client';
import { errorMessage } from '$lib/errors';
import { keepNearbyKinds } from '$lib/nearby/kept-kinds';
import { freeName, type ProfileInFile, type ProfilesFile } from '$lib/profiles-file';

/* A profile from the file the engine would not create, under its name in
the file. The reason is meant for a developer rather than the user. */
export type RefusedProfile = { name: string; reason: string };

export type ImportOutcome = { added: ProfileModel[]; refused: RefusedProfile[] };

/* How an import the user started ended: with the profiles it added and
refused, on a file that is not a file of profiles, or on a file the shell
could not read. */
export type ImportReport =
	| { status: 'done'; outcome: ImportOutcome }
	| { status: 'unreadable' }
	| { status: 'failed'; reason: string };

/* Adds every profile in the file as a new one, never touching those already
kept. A profile named like one already kept gets a free number after its
name. One the engine refuses is left out, and the rest still come in. */
export async function importProfiles(
	client: Pick<SidecarClient, 'createProfile'>,
	profiles: readonly ProfileInFile[],
	keptNames: Iterable<string>
): Promise<ImportOutcome> {
	const taken = new Set(keptNames);
	const added: ProfileModel[] = [];
	const refused: RefusedProfile[] = [];
	// One after another, so each name is checked against those added before it.
	for (const { profile, nearbyKinds } of profiles) {
		const name = freeName(profile.name, taken);
		let created: ProfileModel;
		try {
			created = await client.createProfile({ ...profile, name });
		} catch (error) {
			const reason = error instanceof ApiError && error.reason !== null ? error.reason : errorMessage(error);
			refused.push({ name: profile.name, reason });
			continue;
		}
		taken.add(created.name);
		keepNearbyKinds(created.id, nearbyKinds);
		added.push(created);
	}
	return { added, refused };
}

/* Asks the user for a file of profiles and adds every profile in it. Null
when the user chose no file. */
export async function importProfilesFile(
	file: Pick<ProfilesFile, 'open'>,
	client: Pick<SidecarClient, 'createProfile'>,
	keptNames: () => Iterable<string>
): Promise<ImportReport | null> {
	let opened: ProfileInFile[] | 'unreadable' | null;
	try {
		opened = await file.open();
	} catch (error) {
		return { status: 'failed', reason: errorMessage(error) };
	}
	if (opened === null) return null;
	if (opened === 'unreadable') return { status: 'unreadable' };
	// Taken once the file is chosen, so a profile added while the dialog was
	// open keeps its name.
	return { status: 'done', outcome: await importProfiles(client, opened, keptNames()) };
}
