export interface DevlogPost {
	slug: string;
	title: string;
	date: string;
	summary: string;
}

// Newest first. Each post's text lives next to this file as <slug>.md.
export const POSTS: DevlogPost[] = [
	{
		slug: 'each-flat-once',
		title: 'Each flat once',
		date: '2026-10-11',
		summary:
			'The same flat on two portals used to be two rows in the inbox. Now it is one, and what you have seen follows the flat, not the posting.'
	},
	{
		slug: 'a-list-and-a-detail-view',
		title: 'A list and a detail view',
		date: '2026-10-10',
		summary:
			'The inbox became a list beside the selected listing, with favourites, a price history per portal and a pin on the map.'
	},
	{
		slug: 'scoring-you-can-see',
		title: 'Scoring you can see',
		date: '2026-10-10',
		summary:
			'The profile editor is finished, and scoring got simpler: weights set directly on a split bar, previewed live on example listings.'
	},
	{
		slug: 'the-profile-editor-takes-shape',
		title: 'The profile editor takes shape',
		date: '2026-10-09',
		summary:
			'Prototypes first, scoring moved into the panel, and a clickable map of Czechia whose borders are computed from the nearest village.'
	},
	{
		slug: 'profiles-move-into-the-database',
		title: 'Profiles move into the database',
		date: '2026-10-05',
		summary:
			'Profiles stopped being lines in a config file. They live in SQLite now, have their own API, and point at real places from the RÚIAN register.'
	},
	{
		slug: 'every-listing-gets-its-place',
		title: 'Every listing gets its place',
		date: '2026-10-03',
		summary:
			"A listing's location used to be the portal's line of text. Now it is a set of official places, from the street up to the region."
	},
	{
		slug: 'three-systems-one-build',
		title: 'Three systems, one build',
		date: '2026-10-01',
		summary:
			'The repository split into engine, panel and shell, decisions became ADRs, and GitHub Actions now builds and smoke-tests the app on Linux, Windows and macOS.'
	},
	{
		slug: 'a-real-desktop-app',
		title: 'A real desktop app',
		date: '2026-09-30',
		summary:
			'The Tauri shell now ships a PyInstaller-frozen engine, and each of the two processes notices when the other one dies.'
	},
	{
		slug: 'a-window-around-the-engine',
		title: 'A window around the engine',
		date: '2026-09-28',
		summary:
			'Proving the riskiest part first: a PyInstaller-packaged Python engine started by a Tauri desktop app, and the window waiting until it answers.'
	},
	{
		slug: 'the-panel-and-the-inbox',
		title: 'The panel and the inbox',
		date: '2026-09-24',
		summary:
			'The part of the app you look at, built in Svelte: a typed client for the engine, a CORS surprise and why Czech needs three plural forms.'
	},
	{
		slug: 'the-engine-learns-to-talk',
		title: 'The engine learns to talk',
		date: '2026-09-23',
		summary:
			'Before there could be a desktop app, the engine needed a way to be asked things. It got a FastAPI server with an OpenAPI contract and Server-Sent Events.'
	}
];
