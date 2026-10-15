import { marked } from 'marked';
import { POSTS, type DevlogPost } from '$lib/devlog/posts';

const WORDS_PER_MINUTE = 200;

const BODIES = import.meta.glob<string>('../devlog/*.md', {
	query: '?raw',
	import: 'default',
	eager: true
});

export interface DevlogEntry {
	post: DevlogPost;
	minutesToRead: number;
}

export interface RenderedDevlogPost {
	post: DevlogPost;
	minutesToRead: number;
	html: string;
}

function bodyOf(post: DevlogPost): string {
	const body = BODIES[`../devlog/${post.slug}.md`];
	if (body === undefined) throw new Error(`Devlog post ${post.slug} has no ${post.slug}.md`);
	return body;
}

function minutesToRead(body: string): number {
	const words = body.split(/\s+/).filter((word) => word !== '').length;
	return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

export function listDevlog(): DevlogEntry[] {
	return POSTS.map((post) => ({ post, minutesToRead: minutesToRead(bodyOf(post)) }));
}

export function renderDevlogPost(post: DevlogPost): RenderedDevlogPost {
	const body = bodyOf(post);
	return {
		post,
		minutesToRead: minutesToRead(body),
		html: marked.parse(body, { async: false })
	};
}
