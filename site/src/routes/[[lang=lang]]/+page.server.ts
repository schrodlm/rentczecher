import type { EntryGenerator, PageServerLoad } from './$types';
import shellConfig from '../../../../shell/tauri.conf.json';
import { ALTERNATE_LANGUAGES, DEFAULT_LANGUAGE } from '$lib/i18n';
import { listDevlog } from '$lib/server/devlog';

const DEVLOG_POSTS_SHOWN = 3;

export const entries: EntryGenerator = () => [
	{ lang: undefined },
	...ALTERNATE_LANGUAGES.map((lang) => ({ lang }))
];

export const load: PageServerLoad = ({ params }) => {
	return {
		lang: params.lang ?? DEFAULT_LANGUAGE,
		appVersion: shellConfig.version,
		latestDevlog: listDevlog().slice(0, DEVLOG_POSTS_SHOWN)
	};
};
