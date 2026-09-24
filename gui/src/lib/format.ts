const NBSP = ' ';

export function formatPrice(price: number): string {
	return `${price.toLocaleString('cs-CZ').replace(/\s/g, NBSP)}${NBSP}Kč`;
}

export function formatPricePerM2(price: number, sizeM2: number): string | null {
	if (sizeM2 <= 0) return null;
	const perM2 = Math.round(price / sizeM2);
	return `${perM2.toLocaleString('cs-CZ').replace(/\s/g, NBSP)}${NBSP}Kč/m²`;
}

export function daysSince(isoTimestamp: string, now: Date = new Date()): number {
	const seen = new Date(isoTimestamp);
	const msPerDay = 24 * 60 * 60 * 1000;
	return Math.floor((now.getTime() - seen.getTime()) / msPerDay);
}
