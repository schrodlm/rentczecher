import { invoke } from '@tauri-apps/api/core';
import type { NewProfileBody, PlaceRef, ProfileModel } from '$lib/api/client';
import type { components } from '$lib/api/types.gen';
import { NEARBY_KIND_ORDER, type NearbyKind } from '$lib/nearby/kinds';

type CriteriaBody = components['schemas']['CriteriaBody'];
type PreferencesBody = components['schemas']['PreferencesBody'];

/* A profile as a file carries it from one computer to another: what the
engine needs to create it again, and the kinds of place it shows nearby. */
export type ProfileInFile = { profile: NewProfileBody; nearbyKinds: NearbyKind[] };

// The format this panel writes. A file of any other version is not read, so
// it is never misread.
const VERSION = 1;

/* What creating the stored profile again takes. Places keep only their kind
and code, which name the same place on every computer. */
export function newProfileBodyOf(stored: ProfileModel): NewProfileBody {
	const criteria = stored.criteria;
	const preferences = stored.preferences;
	return {
		name: stored.name,
		portals: [...stored.portals],
		criteria: {
			offer_type: criteria.offer_type,
			estate_type: criteria.estate_type,
			place: { kind: criteria.place.kind, code: criteria.place.code },
			min_price: criteria.min_price,
			max_price: criteria.max_price,
			min_size_m2: criteria.min_size_m2,
			max_size_m2: criteria.max_size_m2,
			min_land_m2: criteria.min_land_m2,
			dispositions: [...criteria.dispositions]
		},
		preferences: {
			price_per_m2_weight: preferences.price_per_m2_weight,
			disposition_weight: preferences.disposition_weight,
			preferred_dispositions: [...preferences.preferred_dispositions],
			size_weight: preferences.size_weight,
			preferred_size_m2: preferences.preferred_size_m2,
			place_weight: preferences.place_weight,
			preferred_places: preferences.preferred_places.map((place) => ({ kind: place.kind, code: place.code })),
			land_weight: preferences.land_weight,
			preferred_land_m2: preferences.preferred_land_m2,
			price_weight: preferences.price_weight,
			preferred_price: preferences.preferred_price
		}
	};
}

export function serializeProfilesFile(profiles: readonly ProfileInFile[]): string {
	const written = profiles.map(({ profile, nearbyKinds }) => ({
		name: profile.name,
		portals: profile.portals,
		criteria: profile.criteria,
		preferences: profile.preferences,
		nearby_kinds: nearbyKinds
	}));
	return JSON.stringify({ version: VERSION, profiles: written }, null, 2) + '\n';
}

/* Null when the text is not a file of profiles this panel writes. Every
field is read by name and type here. The engine checks their values when it
creates the profile, so a profile edited into something invalid is refused
there. */
export function parseProfilesFile(text: string): ProfileInFile[] | null {
	let parsed: unknown;
	try {
		// Some editors start a UTF-8 file with a byte order mark.
		parsed = JSON.parse(text.replace(/^\uFEFF/, ''));
	} catch {
		return null;
	}
	try {
		const file = record(parsed);
		if (file.version !== VERSION) return null;
		return list(file, 'profiles').map(readProfile);
	} catch (error) {
		if (error instanceof Unreadable) return null;
		throw error;
	}
}

function readProfile(written: unknown): ProfileInFile {
	const profile = record(written);
	const criteria = record(profile.criteria);
	const preferences = record(profile.preferences);
	const name = string(profile, 'name').trim();
	if (name === '') throw new Unreadable();
	const nearbyKinds = profile.nearby_kinds === undefined ? [] : list(profile, 'nearby_kinds');
	return {
		profile: {
			name,
			portals: strings(profile, 'portals') as NewProfileBody['portals'],
			criteria: {
				offer_type: string(criteria, 'offer_type') as CriteriaBody['offer_type'],
				estate_type: string(criteria, 'estate_type') as CriteriaBody['estate_type'],
				place: place(criteria.place),
				min_price: numberOrNull(criteria, 'min_price'),
				max_price: numberOrNull(criteria, 'max_price'),
				min_size_m2: numberOrNull(criteria, 'min_size_m2'),
				max_size_m2: numberOrNull(criteria, 'max_size_m2'),
				min_land_m2: numberOrNull(criteria, 'min_land_m2'),
				dispositions: strings(criteria, 'dispositions') as CriteriaBody['dispositions']
			},
			preferences: {
				price_per_m2_weight: number(preferences, 'price_per_m2_weight'),
				disposition_weight: number(preferences, 'disposition_weight'),
				preferred_dispositions: strings(preferences, 'preferred_dispositions') as PreferencesBody['preferred_dispositions'],
				size_weight: number(preferences, 'size_weight'),
				preferred_size_m2: numberOrNull(preferences, 'preferred_size_m2'),
				place_weight: number(preferences, 'place_weight'),
				preferred_places: list(preferences, 'preferred_places').map(place),
				land_weight: number(preferences, 'land_weight'),
				preferred_land_m2: numberOrNull(preferences, 'preferred_land_m2'),
				price_weight: number(preferences, 'price_weight'),
				preferred_price: numberOrNull(preferences, 'preferred_price')
			}
		},
		nearbyKinds: NEARBY_KIND_ORDER.filter((kind) => nearbyKinds.includes(kind))
	};
}

/* A field missing or of another type than this panel writes, which makes
the whole file unreadable. */
class Unreadable extends Error {}

function record(value: unknown): Record<string, unknown> {
	if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new Unreadable();
	return value as Record<string, unknown>;
}

function place(value: unknown): PlaceRef {
	const written = record(value);
	return { kind: string(written, 'kind') as PlaceRef['kind'], code: number(written, 'code') };
}

function string(written: Record<string, unknown>, field: string): string {
	const value = written[field];
	if (typeof value !== 'string') throw new Unreadable();
	return value;
}

function number(written: Record<string, unknown>, field: string): number {
	const value = written[field];
	if (typeof value !== 'number') throw new Unreadable();
	return value;
}

function numberOrNull(written: Record<string, unknown>, field: string): number | null {
	return written[field] === null ? null : number(written, field);
}

function list(written: Record<string, unknown>, field: string): unknown[] {
	const value = written[field];
	if (!Array.isArray(value)) throw new Unreadable();
	return value;
}

function strings(written: Record<string, unknown>, field: string): string[] {
	const values = list(written, field);
	if (!values.every((value) => typeof value === 'string')) throw new Unreadable();
	return values as string[];
}

/* The name, or when a profile already goes by it, the name numbered with
the first free number. A name already numbered is numbered afresh, so a
profile imported twice reads "Praha (3)" rather than "Praha (2) (2)". */
export function freeName(name: string, taken: ReadonlySet<string>): string {
	if (!taken.has(name)) return name;
	const unnumbered = name.replace(/ \(\d+\)$/, '');
	let number = 2;
	while (taken.has(`${unnumbered} (${number})`)) number += 1;
	return `${unnumbered} (${number})`;
}

/* A file of profiles the user picks in the system's own dialog. The shell
only moves its text, and the panel owns its shape. */
export class ProfilesFile {
	/* False when the user closed the dialog without saving. */
	async save(profiles: readonly ProfileInFile[]): Promise<boolean> {
		return invoke<boolean>('save_profiles_file', { contents: serializeProfilesFile(profiles) });
	}

	/* Null when the user closed the dialog without choosing, and 'unreadable'
	when the file they chose is not a file of profiles. */
	async open(): Promise<ProfileInFile[] | 'unreadable' | null> {
		const text = await invoke<string | null>('open_profiles_file');
		if (text === null) return null;
		return parseProfilesFile(text) ?? 'unreadable';
	}
}
