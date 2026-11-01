/* The inbox's sections, and which of them the user folded away, kept on
this machine. */
export type Section = 'new' | 'updated' | 'favourite' | 'viewed';

export const SECTIONS: readonly Section[] = ['new', 'updated', 'favourite', 'viewed'];
const KEY = 'rentczecher.foldedSections';

// The browser may refuse its storage, as in a private window, and then every
// section opens unfolded.
export function foldedSections(): Section[] {
	try {
		const kept: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]');
		return Array.isArray(kept) ? SECTIONS.filter((section) => kept.includes(section)) : [];
	} catch {
		return [];
	}
}

export function keepFoldedSections(folded: readonly Section[]): void {
	try {
		localStorage.setItem(KEY, JSON.stringify(folded));
	} catch {
		return;
	}
}
