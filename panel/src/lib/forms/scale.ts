/* The positions a slider moves through, low to high. They are not evenly
spaced: prices step by thousands where most searches sit and by tens of
thousands above that. */
export class Scale {
	constructor(readonly stops: readonly number[]) {}

	get lastIndex(): number {
		return this.stops.length - 1;
	}

	valueAt(index: number): number {
		return this.stops[index];
	}

	/* The position closest to a value, so a typed number that falls between
	stops still places the handle. */
	nearestIndex(value: number): number {
		let nearest = 0;
		for (let index = 1; index < this.stops.length; index++) {
			if (Math.abs(this.stops[index] - value) < Math.abs(this.stops[nearest] - value)) nearest = index;
		}
		return nearest;
	}
}

export const RENT_SCALE = new Scale([
	0, 3000, 5000, 7500, 10000, 12500, 15000, 17500, 20000, 22500, 25000, 30000, 35000, 40000, 50000, 60000, 80000,
	100000
]);
export const SALE_SCALE = new Scale([
	0, 500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000, 3_000_000, 3_500_000, 4_000_000, 5_000_000, 6_000_000,
	7_000_000, 8_000_000, 10_000_000, 12_000_000, 15_000_000, 20_000_000, 30_000_000
]);
export const SIZE_SCALE = new Scale([0, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90, 100, 120, 150, 200, 250, 300]);
export const LAND_SCALE = new Scale([0, 100, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000, 3000, 5000, 10000]);

export function priceScale(offerType: 'rent' | 'sale'): Scale {
	return offerType === 'rent' ? RENT_SCALE : SALE_SCALE;
}

/* A number as a slider's box shows it, thousands spaced the Czech way, and
an empty box for no number. parseTypedNumber reads it back. */
export function writeTypedNumber(value: number | null): string {
	return value === null ? '' : value.toLocaleString('cs-CZ');
}

/* A whole number typed in a slider's box, spaces between thousands allowed,
or null when the box is empty or holds no number. */
export function parseTypedNumber(text: string): number | null {
	const digits = text.replace(/\s/g, '');
	if (!/^\d+$/.test(digits)) return null;
	return Number(digits);
}
