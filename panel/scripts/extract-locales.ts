/*
The msgid extractor: scans gui/src call sites and keeps gui/locales/cs.po
honest against them.

Default mode checks and exits nonzero when the catalog and the source
disagree: a msgid in source with no catalog entry, an entry left
untranslated, a plural shape mismatch, or an orphaned entry whose call
sites are all gone. --write appends missing msgids to cs.po with empty
msgstrs to fill in. It never rewrites or removes existing entries, so
orphans and blanks are always resolved by hand in the .po file.

Call sites must be static string literals for the scan to see them:
t('Loading...') and tn('{count} profile', '{count} profiles', count).
A msgid built at runtime defeats both this scan and the catalog contract.
*/

import { appendFileSync, readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { po } from 'gettext-parser';

import { pluralCountFromHeader } from './po-header.js';

const GUI_DIR = join(import.meta.dirname, '..');
const SRC_DIR = join(GUI_DIR, 'src');
const CS_PO_PATH = join(GUI_DIR, 'locales', 'cs.po');

const T_CALL = /(?<![\w$])t\(\s*(['"])((?:\\.|(?!\1).)*)\1/g;
const TN_CALL = /(?<![\w$])tn\(\s*(['"])((?:\\.|(?!\1).)*)\1\s*,\s*(['"])((?:\\.|(?!\3).)*)\3/g;

type CallSites = Map<string, { plural: string | null; files: Set<string> }>;

function* sourceFiles(dir: string): Generator<string> {
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		const path = join(dir, entry.name);
		if (entry.isDirectory()) {
			yield* sourceFiles(path);
		} else if (/\.(svelte|ts)$/.test(entry.name)) {
			yield path;
		}
	}
}

function unescape(literal: string): string {
	return literal.replace(/\\(['"\\])/g, '$1');
}

function record(sites: CallSites, msgid: string, plural: string | null, file: string): void {
	const existing = sites.get(msgid);
	if (existing === undefined) {
		sites.set(msgid, { plural, files: new Set([file]) });
		return;
	}
	if (existing.plural !== plural) {
		throw new Error(
			`"${msgid}" is used both with and without a plural form (${[...existing.files, file].join(', ')})`
		);
	}
	existing.files.add(file);
}

function collectCallSites(): CallSites {
	const sites: CallSites = new Map();
	for (const path of sourceFiles(SRC_DIR)) {
		const source = readFileSync(path, 'utf-8');
		const file = relative(GUI_DIR, path);
		// tn first: the t pattern would otherwise claim a tn call's first
		// argument as a plain message.
		const withoutTn = source.replace(TN_CALL, (match, _q1, msgid, _q2, plural) => {
			record(sites, unescape(msgid), unescape(plural), file);
			return '';
		});
		for (const match of withoutTn.matchAll(T_CALL)) {
			record(sites, unescape(match[2]), null, file);
		}
	}
	return sites;
}

function escapePo(text: string): string {
	return text.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function entryBlock(msgid: string, plural: string | null, pluralCount: number): string {
	const lines = [`msgid "${escapePo(msgid)}"`];
	if (plural === null) {
		lines.push('msgstr ""');
	} else {
		lines.push(`msgid_plural "${escapePo(plural)}"`);
		for (let form = 0; form < pluralCount; form++) {
			lines.push(`msgstr[${form}] ""`);
		}
	}
	return '\n' + lines.join('\n') + '\n';
}

function main(): void {
	const write = process.argv.includes('--write');
	const sites = collectCallSites();

	const parsed = po.parse(readFileSync(CS_PO_PATH));
	const pluralCount = pluralCountFromHeader(parsed.headers['Plural-Forms']);
	const entries = Object.values(parsed.translations[''] ?? {}).filter((e) => e.msgid !== '');

	const problems: string[] = [];
	const missing: string[] = [];

	for (const [msgid, site] of [...sites].sort()) {
		const files = [...site.files].join(', ');
		const entry = entries.find((e) => e.msgid === msgid);
		if (entry === undefined) {
			missing.push(msgid);
			problems.push(`missing from cs.po: "${msgid}" (${files})`);
			continue;
		}
		const entryPlural = entry.msgid_plural ?? null;
		if (entryPlural !== site.plural) {
			problems.push(`plural shape differs between source and cs.po: "${msgid}" (${files})`);
			continue;
		}
		const expectedForms = site.plural === null ? 1 : pluralCount;
		if (entry.msgstr.length !== expectedForms || entry.msgstr.some((form) => form === '')) {
			problems.push(`untranslated in cs.po: "${msgid}" (${files})`);
		}
	}
	for (const entry of entries) {
		if (!sites.has(entry.msgid)) {
			problems.push(`orphaned in cs.po, no call site: "${entry.msgid}"`);
		}
	}

	if (write && missing.length > 0) {
		for (const msgid of missing) {
			appendFileSync(CS_PO_PATH, entryBlock(msgid, sites.get(msgid)!.plural, pluralCount));
		}
		console.log(`Appended ${missing.length} empty entr${missing.length === 1 ? 'y' : 'ies'} to cs.po, fill in the msgstrs.`);
		return;
	}

	if (problems.length > 0) {
		for (const problem of problems) {
			console.error(problem);
		}
		process.exit(1);
	}
	console.log(`cs.po covers all ${sites.size} msgid(s) in gui/src.`);
}

main();
