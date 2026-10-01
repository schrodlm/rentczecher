/*
Parses the plural form count out of a catalog's Plural-Forms header, e.g.
"nplurals=3; plural=(n==1) ? 0 : ...". Shared by the compile and extract
scripts so both always agree on what a valid catalog is.
*/

export function pluralCountFromHeader(header: string | undefined): number {
	const match = header?.match(/nplurals\s*=\s*(\d+)/);
	if (!match) {
		throw new Error(`Plural-Forms header missing or malformed: ${header ?? '(absent)'}`);
	}
	return Number(match[1]);
}
