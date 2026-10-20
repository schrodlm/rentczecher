import type { Translator } from '$lib/i18n/translator';

export type NearbyKind =
	| 'metro'
	| 'tram'
	| 'train'
	| 'bus'
	| 'supermarket'
	| 'school'
	| 'kindergarten'
	| 'pharmacy'
	| 'park'
	| 'theatre'
	| 'cinema';

/* A kind of place the panel can find near a flat, and the OpenStreetMap
filters that select it. */
export type NearbyKindShown = { kind: NearbyKind; filters: readonly string[] };

export const NEARBY_KINDS: readonly NearbyKindShown[] = [
	{ kind: 'metro', filters: ['nwr["railway"="station"]["station"="subway"]'] },
	{ kind: 'tram', filters: ['node["railway"="tram_stop"]'] },
	{ kind: 'train', filters: ['nwr["railway"~"^(station|halt)$"]["station"!~"^(subway|light_rail)$"]'] },
	{ kind: 'bus', filters: ['node["highway"="bus_stop"]'] },
	{ kind: 'supermarket', filters: ['nwr["shop"="supermarket"]'] },
	{ kind: 'school', filters: ['nwr["amenity"="school"]'] },
	{ kind: 'kindergarten', filters: ['nwr["amenity"="kindergarten"]'] },
	{ kind: 'pharmacy', filters: ['nwr["amenity"="pharmacy"]'] },
	{ kind: 'park', filters: ['nwr["leisure"="park"]'] },
	{ kind: 'theatre', filters: ['nwr["amenity"="theatre"]'] },
	{ kind: 'cinema', filters: ['nwr["amenity"="cinema"]'] }
];

export const NEARBY_KIND_ORDER: readonly NearbyKind[] = NEARBY_KINDS.map((each) => each.kind);

export function kindName(kind: NearbyKind, t: Translator): string {
	if (kind === 'metro') return t.t('Metro');
	if (kind === 'tram') return t.t('Tram');
	if (kind === 'train') return t.t('Train');
	if (kind === 'bus') return t.t('Bus');
	if (kind === 'supermarket') return t.t('Supermarket');
	if (kind === 'school') return t.t('School');
	if (kind === 'kindergarten') return t.t('Kindergarten');
	if (kind === 'pharmacy') return t.t('Pharmacy');
	if (kind === 'park') return t.t('Park');
	if (kind === 'theatre') return t.t('Theatre');
	return t.t('Cinema');
}
