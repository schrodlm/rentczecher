import { afterEach, describe, expect, test, vi } from 'vitest';

const opened = vi.hoisted(() => ({ urls: [] as string[], inApp: false }));

vi.mock('@tauri-apps/api/core', () => ({
	isTauri: () => opened.inApp,
	invoke: async (command: string, args: { url: string }) => {
		if (command === 'open_in_browser') opened.urls.push(args.url);
	}
}));

const { opensInBrowser } = await import('./browser-link');

/* A link using the action, and a click on it that says whether the link was
left to the page. The page's own following of the link is stopped after, as
the test environment cannot navigate. */
function linkTo(url: string): { click: () => boolean; destroy: () => void } {
	const page = document.body.appendChild(document.createElement('div'));
	const link = page.appendChild(document.createElement('a'));
	link.href = url;
	link.target = '_blank';
	const action = opensInBrowser(link);
	let leftToThePage = false;
	page.addEventListener('click', (event) => {
		leftToThePage = !event.defaultPrevented;
		event.preventDefault();
	});
	return {
		click: () => {
			link.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
			return leftToThePage;
		},
		destroy: action.destroy
	};
}

afterEach(() => {
	opened.urls = [];
	opened.inApp = false;
	document.body.innerHTML = '';
});

describe('opensInBrowser', () => {
	test('hands a clicked link to the default browser in the app', () => {
		opened.inApp = true;
		const { click } = linkTo('https://www.sreality.cz/detail/1');
		expect(click()).toBe(false);
		expect(opened.urls).toEqual(['https://www.sreality.cz/detail/1']);
	});

	test('leaves the link to the page outside the app', () => {
		const { click } = linkTo('https://www.sreality.cz/detail/1');
		expect(click()).toBe(true);
		expect(opened.urls).toEqual([]);
	});

	test('stops handing the link over once it is gone', () => {
		opened.inApp = true;
		const { click, destroy } = linkTo('https://www.bezrealitky.cz/1');
		destroy();
		expect(click()).toBe(true);
		expect(opened.urls).toEqual([]);
	});
});
