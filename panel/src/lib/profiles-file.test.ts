import { afterEach, describe, expect, test, vi } from 'vitest';
import fileOfVersion1 from '$lib/test-support/profiles-file-v1.json?raw';
import { storedProfile } from '$lib/test-support/stored-profile';

const shell = vi.hoisted(() => ({
	calls: [] as { command: string; args: unknown }[],
	reply: null as unknown
}));

vi.mock('@tauri-apps/api/core', () => ({
	invoke: async (command: string, args: unknown) => {
		shell.calls.push({ command, args });
		return shell.reply;
	}
}));

const { freeName, newProfileBodyOf, parseProfilesFile, ProfilesFile, serializeProfilesFile } = await import(
	'$lib/profiles-file'
);

afterEach(() => {
	shell.calls = [];
	shell.reply = null;
});

describe('newProfileBodyOf', () => {
	test('keeps every criterion and preference, and each place only by its kind and code', () => {
		const body = newProfileBodyOf(storedProfile('p1', 'Praha byty'));
		expect(body).toEqual({
			name: 'Praha byty',
			portals: ['sreality', 'remax'],
			criteria: {
				offer_type: 'rent',
				estate_type: 'flat',
				place: { kind: 'obec', code: 554782 },
				min_price: 15000,
				max_price: 30000,
				min_size_m2: 40,
				max_size_m2: 90,
				min_land_m2: null,
				dispositions: ['2+kk', '2+1']
			},
			preferences: {
				price_per_m2_weight: 10,
				disposition_weight: 20,
				preferred_dispositions: ['2+kk'],
				size_weight: 20,
				preferred_size_m2: 70,
				place_weight: 10,
				preferred_places: [{ kind: 'mestska_cast', code: 500186 }],
				land_weight: 0,
				preferred_land_m2: null,
				price_weight: 40,
				preferred_price: 22000
			}
		});
	});
});

describe('parseProfilesFile', () => {
	test('reads a file the first version of the format wrote', () => {
		expect(parseProfilesFile(fileOfVersion1)).toEqual([
			{ profile: newProfileBodyOf(storedProfile('p1', 'Praha byty')), nearbyKinds: ['metro', 'park'] }
		]);
	});

	test('reads a file that starts with a byte order mark', () => {
		expect(parseProfilesFile('\uFEFF' + fileOfVersion1)).toHaveLength(1);
	});

	test('reads a profile name without the spaces around it', () => {
		const edited = JSON.parse(fileOfVersion1);
		edited.profiles[0].name = '  Praha byty ';
		expect(parseProfilesFile(JSON.stringify(edited))?.[0].profile.name).toBe('Praha byty');
	});

	test('reads nothing when a profile has a blank name', () => {
		const edited = JSON.parse(fileOfVersion1);
		edited.profiles[0].name = '   ';
		expect(parseProfilesFile(JSON.stringify(edited))).toBeNull();
	});

	test('reads nothing when a field holds another type than the format writes', () => {
		const edits: ((profile: Record<string, any>) => void)[] = [
			(profile) => (profile.portals = 'sreality'),
			(profile) => (profile.criteria.min_price = '15000'),
			(profile) => (profile.criteria.place = 'Praha'),
			(profile) => (profile.preferences.size_weight = null),
			(profile) => (profile.preferences.preferred_dispositions = [2]),
			(profile) => (profile.nearby_kinds = 'metro')
		];
		for (const edit of edits) {
			const edited = JSON.parse(fileOfVersion1);
			edit(edited.profiles[0]);
			expect(parseProfilesFile(JSON.stringify(edited))).toBeNull();
		}
	});

	test('reads back the profiles and nearby kinds a file was written with', () => {
		const written = [
			{ profile: newProfileBodyOf(storedProfile('p1', 'Praha byty')), nearbyKinds: ['metro' as const, 'park' as const] },
			{ profile: newProfileBodyOf(storedProfile('p2', 'Brno')), nearbyKinds: [] }
		];
		expect(parseProfilesFile(serializeProfilesFile(written))).toEqual(written);
	});

	test('reads a file without profiles as an empty list', () => {
		expect(parseProfilesFile(serializeProfilesFile([]))).toEqual([]);
	});

	test('keeps only the nearby kinds it knows, in the order the panel lists them', () => {
		const text = serializeProfilesFile([{ profile: newProfileBodyOf(storedProfile('p1', 'Praha')), nearbyKinds: [] }]);
		const edited = JSON.parse(text);
		edited.profiles[0].nearby_kinds = ['park', 'casino', 'metro'];
		expect(parseProfilesFile(JSON.stringify(edited))?.[0].nearbyKinds).toEqual(['metro', 'park']);
	});

	test('reads a profile without nearby kinds as showing none', () => {
		const text = serializeProfilesFile([{ profile: newProfileBodyOf(storedProfile('p1', 'Praha')), nearbyKinds: ['metro'] }]);
		const edited = JSON.parse(text);
		delete edited.profiles[0].nearby_kinds;
		expect(parseProfilesFile(JSON.stringify(edited))?.[0].nearbyKinds).toEqual([]);
	});

	test('reads nothing that is not JSON, or not a file of profiles of this version', () => {
		expect(parseProfilesFile('not json')).toBeNull();
		expect(parseProfilesFile('[]')).toBeNull();
		expect(parseProfilesFile(JSON.stringify({ version: 2, profiles: [] }))).toBeNull();
		expect(parseProfilesFile(JSON.stringify({ version: 1 }))).toBeNull();
		expect(parseProfilesFile(JSON.stringify({ theme: 'dark', language: 'cs', version: 1 }))).toBeNull();
	});

	test('reads nothing when any profile lacks its name, portals, search or preferences', () => {
		const profile = JSON.parse(serializeProfilesFile([{ profile: newProfileBodyOf(storedProfile('p1', 'Praha')), nearbyKinds: [] }])).profiles[0];
		for (const missing of ['name', 'portals', 'criteria', 'preferences']) {
			const broken = { ...profile };
			delete broken[missing];
			expect(parseProfilesFile(JSON.stringify({ version: 1, profiles: [profile, broken] }))).toBeNull();
		}
	});
});

describe('freeName', () => {
	test('keeps a name no profile goes by', () => {
		expect(freeName('Praha', new Set(['Brno']))).toBe('Praha');
	});

	test('numbers a taken name with the first free number from 2', () => {
		expect(freeName('Praha', new Set(['Praha']))).toBe('Praha (2)');
		expect(freeName('Praha', new Set(['Praha', 'Praha (2)', 'Praha (3)']))).toBe('Praha (4)');
	});

	test('numbers a taken numbered name afresh rather than numbering it again', () => {
		expect(freeName('Praha (2)', new Set(['Praha', 'Praha (2)']))).toBe('Praha (3)');
	});

	test('keeps a numbered name no profile goes by', () => {
		expect(freeName('Praha (2)', new Set(['Praha']))).toBe('Praha (2)');
	});
});

describe('ProfilesFile', () => {
	const PRAHA = { profile: newProfileBodyOf(storedProfile('p1', 'Praha')), nearbyKinds: ['tram' as const] };

	test('hands the shell the file to save, and tells whether it was saved', async () => {
		shell.reply = true;
		expect(await new ProfilesFile().save([PRAHA])).toBe(true);
		expect(shell.calls).toEqual([{ command: 'save_profiles_file', args: { contents: serializeProfilesFile([PRAHA]) } }]);
	});

	test('reads the profiles in the file the user chose', async () => {
		shell.reply = serializeProfilesFile([PRAHA]);
		expect(await new ProfilesFile().open()).toEqual([PRAHA]);
		expect(shell.calls).toEqual([{ command: 'open_profiles_file', args: undefined }]);
	});

	test('opens nothing when the user chose no file', async () => {
		shell.reply = null;
		expect(await new ProfilesFile().open()).toBeNull();
	});

	test('reports a chosen file that is not a file of profiles as unreadable', async () => {
		shell.reply = '{"theme": "dark"}';
		expect(await new ProfilesFile().open()).toBe('unreadable');
	});
});
