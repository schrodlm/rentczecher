import type { NamedPlace } from '$lib/api/client';
import type { Translator } from '$lib/i18n/translator';

/* A place as the user reads it, its kind and what it lies in after the name,
which tells same-named places apart: "Holešovice (část obce, Praha)". */
export function placeLabel(place: NamedPlace, t: Translator): string {
	const context = [kindName(place.kind, t), place.obec, place.okres].filter((part) => part !== null);
	return `${place.name ?? `${place.kind} ${place.code}`} (${context.join(', ')})`;
}

function kindName(kind: NamedPlace['kind'], t: Translator): string {
	if (kind === 'kraj') return t.t('region');
	if (kind === 'okres') return t.t('district');
	if (kind === 'obec') return t.t('municipality');
	if (kind === 'obvod') return t.t('city district');
	if (kind === 'mestska_cast') return t.t('borough');
	if (kind === 'cast_obce') return t.t('part of a municipality');
	return t.t('street');
}
