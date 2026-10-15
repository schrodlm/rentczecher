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
		slug: 'every-listing-gets-its-place',
		title: 'Every listing gets its place',
		date: '2026-10-03',
		summary:
			"A listing's location used to be the portal's line of text. Now it is a set of official places, from the street up to the region."
	}
];
