// SvelteKit finds a route's matcher only by this file's name: [[lang=lang]] loads
// the `match` export from params/lang.ts. The check itself lives with the language list.
export { isAlternateLanguage as match } from '$lib/i18n';
