import type { PageServerLoad } from './$types';
import { listDevlog } from '$lib/server/devlog';

export const load: PageServerLoad = () => {
	return { entries: listDevlog() };
};
