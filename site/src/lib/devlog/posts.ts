export interface DevlogPost {
	slug: string;
	title: string;
	date: string;
	summary: string;
}

// Newest first. Each post's text lives next to this file as <slug>.md.
export const POSTS: DevlogPost[] = [
	{
		slug: 'changed-since-you-looked',
		title: 'Changed since you looked',
		date: '2026-11-01',
		summary:
			'A viewed flat that gets cheaper, dearer or posted on another portal moves into an Updated section with the change highlighted, and the matcher stops merging different flats on one street. This makes version 0.4.0.'
	},
	{
		slug: 'a-fourth-portal-idnes-reality',
		title: 'A fourth portal: iDNES Reality',
		date: '2026-10-31',
		summary:
			'iDNES Reality joins RE/MAX as a portal on from the start, read within what its robots.txt allows, searched by RÚIAN codes and with its galleries, plus a database upgrade that keeps every price history.'
	},
	{
		slug: 'profiles-move-between-computers',
		title: 'Profiles move between computers',
		date: '2026-10-31',
		summary:
			'Save the chosen profiles into a JSON file and add them on another computer, with every place kept by its RÚIAN code. With the updater, this makes version 0.3.0.'
	},
	{
		slug: 'the-app-updates-itself',
		title: 'The app updates itself',
		date: '2026-10-26',
		summary:
			"Tauri's updater offers each new release in the top bar, and every release is signed, so the app installs only what I built."
	},
	{
		slug: 'finding-your-way-around-a-flat',
		title: 'Finding your way around a flat',
		date: '2026-10-20',
		summary:
			'A number, a name and a picture for every flat, a street map from OpenStreetMap, the distance to the nearest metro or school, and a clearer top bar and inbox.'
	},
	{
		slug: 'every-flat-gets-its-photos',
		title: 'Every flat gets its photos',
		date: '2026-10-20',
		summary:
			'The main photo of every new flat after a scan, the whole gallery once you open or star it, and a collage leading the details.'
	},
	{
		slug: 'ready-for-a-first-release',
		title: 'Ready for a first release',
		date: '2026-10-16',
		summary:
			'Search any place down to a street, a cap on how many pages a search reads, releases built from a tag, and one clean database schema. Version 0.1.0 is out as a beta.'
	},
	{
		slug: 'a-front-door-for-the-project',
		title: 'A front door for the project',
		date: '2026-10-16',
		summary:
			'A website, a README you can read in two minutes, the technical docs on pages of their own, and everything checked against what the app really does.'
	},
	{
		slug: 'honest-about-how-it-reads-the-portals',
		title: 'Honest about how it reads the portals',
		date: '2026-10-15',
		summary:
			'The app stopped pretending to be Firefox, keeps Sreality and Bezrealitky off until you turn them on, and forgets what no profile has seen for 90 days.'
	},
	{
		slug: 'is-it-legal-to-release-this',
		title: 'Is it legal to release this?',
		date: '2026-10-14',
		summary:
			'Before going further I checked whether publishing rentczecher is safe. The answer shaped the tool: local, free, linking back to the portals, and licensed GPL.'
	},
	{
		slug: 'a-welcome-and-a-choice-of-language',
		title: 'A welcome and a choice of language',
		date: '2026-10-12',
		summary:
			'The app learned light and dark, Czech and English, and a welcome wizard that asks for both on the first launch.'
	},
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
