import { error } from '@sveltejs/kit';
import type { EntryGenerator, PageServerLoad } from './$types';
import { POSTS } from '$lib/devlog/posts';
import { renderDevlogPost } from '$lib/server/devlog';

export const entries: EntryGenerator = () => POSTS.map((post) => ({ slug: post.slug }));

export const load: PageServerLoad = ({ params }) => {
	const post = POSTS.find((candidate) => candidate.slug === params.slug);
	if (post === undefined) error(404);
	return renderDevlogPost(post);
};
