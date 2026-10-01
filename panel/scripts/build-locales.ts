/*
Converts every panel/locales/<lang>.po catalog into panel/src/lib/i18n/<lang>.json,
consumed at runtime by the translation helper. A catalog entry with a
msgid_plural becomes a JSON array of its ordered plural forms. A plain entry
becomes a JSON string. Each plural entry's form count is validated against
the Plural-Forms header here, at build time, so the runtime can trust every
array's length.
*/

import { po } from 'gettext-parser';
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import type { Catalog } from '../src/lib/i18n/catalog.js';
import { pluralCountFromHeader } from './po-header.js';

const LOCALES_DIR = join(import.meta.dirname, '..', 'locales');
const OUTPUT_DIR = join(import.meta.dirname, '..', 'src', 'lib', 'i18n');

function buildCatalog(poPath: string): Catalog {
	const parsed = po.parse(readFileSync(poPath));
	const pluralCount = pluralCountFromHeader(parsed.headers['Plural-Forms']);

	const messages: Catalog = {};
	for (const context of Object.values(parsed.translations)) {
		for (const entry of Object.values(context)) {
			if (entry.msgid === '') continue; // the header entry, not a message

			if (entry.msgid_plural !== undefined) {
				if (entry.msgstr.length !== pluralCount) {
					throw new Error(
						`${basename(poPath)}: "${entry.msgid}" has ${entry.msgstr.length} plural forms, header declares ${pluralCount}`
					);
				}
				messages[entry.msgid] = entry.msgstr;
			} else {
				messages[entry.msgid] = entry.msgstr[0];
			}
		}
	}

	return messages;
}

function main() {
	mkdirSync(OUTPUT_DIR, { recursive: true });

	const poFiles = readdirSync(LOCALES_DIR).filter((name) => name.endsWith('.po'));
	for (const fileName of poFiles) {
		const lang = basename(fileName, '.po');
		const catalog = buildCatalog(join(LOCALES_DIR, fileName));
		const outputPath = join(OUTPUT_DIR, `${lang}.json`);
		writeFileSync(outputPath, JSON.stringify(catalog, null, '\t') + '\n');
		console.log(`Wrote ${outputPath}`);
	}
}

main();
