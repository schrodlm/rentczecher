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

// jsdom has no PointerEvent, so a pointer event a test fires would carry no
// position. A mouse event with a pointer id stands in.
if (!window.PointerEvent) {
	class StandInPointerEvent extends MouseEvent {
		readonly pointerId: number;

		constructor(type: string, init: PointerEventInit = {}) {
			super(type, init);
			this.pointerId = init.pointerId ?? 0;
		}
	}
	window.PointerEvent = StandInPointerEvent as typeof PointerEvent;
}
