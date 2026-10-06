/* PROTOTYPE, throwaway. Slider stops and number formatting. */

export function kc(n: number): string {
	if (n >= 1_000_000) return `${(n / 1_000_000).toLocaleString('cs-CZ', { maximumFractionDigits: 1 })} mil. Kč`;
	return `${n.toLocaleString('cs-CZ')} Kč`;
}

export function m2(n: number): string {
	return `${n.toLocaleString('cs-CZ')} m²`;
}

const RENT = [0, 3000, 5000, 7500, 10000, 12500, 15000, 17500, 20000, 22500, 25000, 30000, 35000, 40000, 50000, 60000, 80000, 100000];
const SALE = [0, 500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000, 3_000_000, 3_500_000, 4_000_000, 5_000_000, 6_000_000, 7_000_000, 8_000_000, 10_000_000, 12_000_000, 15_000_000, 20_000_000, 30_000_000];

export function priceStops(offer: 'rent' | 'sale'): number[] {
	return offer === 'rent' ? RENT : SALE;
}

export const sizeStops = [0, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90, 100, 120, 150, 200, 250, 300];
export const landStops = [0, 100, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000, 3000, 5000, 10000];
