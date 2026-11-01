import type { components } from '$lib/api/types.gen';
import bezrealitkyLogo from '$lib/assets/portals/bezrealitky.svg';
import idnesLogo from '$lib/assets/portals/idnes.svg';
import remaxLogo from '$lib/assets/portals/remax.svg';
import srealityLogo from '$lib/assets/portals/sreality.svg';

export type Portal = components['schemas']['NewProfileBody']['portals'][number];

/* A portal as the panel shows it. The logos are the portals' own icons,
bundled since the app's content policy loads images only from itself.
optInTerms links the terms of a portal that asks apps not to read it, which
stays off until the user turns it on knowingly, and is null otherwise. */
export type PortalShown = { portal: Portal; name: string; site: string; logo: string; optInTerms: string | null };

export const PORTALS: readonly PortalShown[] = [
	{
		portal: 'sreality',
		name: 'Sreality',
		site: 'sreality.cz',
		logo: srealityLogo,
		optInTerms: 'https://o-seznam.cz/napoveda/sreality/smluvni-podminky-sluzby-sreality-cz/'
	},
	{
		portal: 'bezrealitky',
		name: 'Bezrealitky',
		site: 'bezrealitky.cz',
		logo: bezrealitkyLogo,
		optInTerms: 'https://www.bezrealitky.cz/informace/smluvni-podminky'
	},
	{ portal: 'remax', name: 'RE/MAX', site: 'remax-czech.cz', logo: remaxLogo, optInTerms: null },
	{ portal: 'idnes', name: 'iDNES Reality', site: 'reality.idnes.cz', logo: idnesLogo, optInTerms: null }
];

/* How the panel shows a listing's source, or undefined for a source it
does not know. */
export function shownPortal(source: string): PortalShown | undefined {
	return PORTALS.find((shown) => shown.portal === source);
}
