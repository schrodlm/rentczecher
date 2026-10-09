import type { components } from '$lib/api/types.gen';
import bezrealitkyLogo from '$lib/assets/portals/bezrealitky.svg';
import remaxLogo from '$lib/assets/portals/remax.svg';
import srealityLogo from '$lib/assets/portals/sreality.svg';

export type Portal = components['schemas']['NewProfileBody']['portals'][number];

/* A portal as the panel shows it. The logos are the portals' own icons,
bundled since the app's content policy loads images only from itself. */
export type PortalShown = { portal: Portal; name: string; site: string; logo: string };

export const PORTALS: readonly PortalShown[] = [
	{ portal: 'sreality', name: 'Sreality', site: 'sreality.cz', logo: srealityLogo },
	{ portal: 'bezrealitky', name: 'Bezrealitky', site: 'bezrealitky.cz', logo: bezrealitkyLogo },
	{ portal: 'remax', name: 'RE/MAX', site: 'remax-czech.cz', logo: remaxLogo }
];

/* How the panel shows a listing's source, or undefined for a source it
does not know. */
export function shownPortal(source: string): PortalShown | undefined {
	return PORTALS.find((shown) => shown.portal === source);
}
