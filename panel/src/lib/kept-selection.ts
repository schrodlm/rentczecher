/* The profile and listing the inbox showed, kept across the reload a
language change makes so the panel opens where it was. */
export type KeptSelection = { profileId: string; propertyId: string | null };

const KEY = 'rentczecher.keptSelection';

// The browser may refuse its storage, as in a private window, and then the
// panel simply opens on its first profile.
export function keepSelection(selection: KeptSelection): void {
	try {
		sessionStorage.setItem(KEY, JSON.stringify(selection));
	} catch {
		return;
	}
}

/* The kept selection, read once: a second call finds none. */
export function takeKeptSelection(): KeptSelection | null {
	try {
		const text = sessionStorage.getItem(KEY);
		sessionStorage.removeItem(KEY);
		if (text === null) return null;
		const { profileId, propertyId } = JSON.parse(text) as Record<string, unknown>;
		if (typeof profileId !== 'string') return null;
		return { profileId, propertyId: typeof propertyId === 'string' ? propertyId : null };
	} catch {
		return null;
	}
}
