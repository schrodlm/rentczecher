import '@testing-library/jest-dom/vitest';

// jsdom has no matchMedia, which Svelte's motion reads for the reduced-motion
// preference. A stand-in that matches no query lets animated components run.
if (!window.matchMedia) {
	window.matchMedia = (query: string) =>
		({
			matches: false,
			media: query,
			onchange: null,
			addEventListener: () => {},
			removeEventListener: () => {},
			addListener: () => {},
			removeListener: () => {},
			dispatchEvent: () => false
		}) as MediaQueryList;
}
