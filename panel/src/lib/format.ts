const NBSP = ' ';

function formatNumber(value: number): string {
	return value.toLocaleString('cs-CZ').replace(/\s/g, NBSP);
}

export function formatPrice(price: number): string {
	return `${formatNumber(price)}${NBSP}Kč`;
}

export function formatPricePerM2(price: number, sizeM2: number): string | null {
	if (sizeM2 <= 0) return null;
	return formatPerM2(price / sizeM2);
}

export function formatPerM2(pricePerM2: number): string {
	return `${formatPrice(Math.round(pricePerM2))}/m²`;
}

export function daysSince(isoTimestamp: string, now: Date = new Date()): number {
	const seen = new Date(isoTimestamp);
	const msPerDay = 24 * 60 * 60 * 1000;
	return Math.floor((now.getTime() - seen.getTime()) / msPerDay);
}

export function sourceInitial(source: string): string {
	return source.charAt(0).toUpperCase();
}

export function formatArea(m2: number): string {
	return `${formatNumber(m2)}${NBSP}m²`;
}
