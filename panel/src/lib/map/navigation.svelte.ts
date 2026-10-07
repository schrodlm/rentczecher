import type { NamedPlace } from '$lib/api/client';
import {
	districtOf,
	districtsOf,
	isPraha,
	krajByCode,
	krajOf,
	KRAJE,
	MAP_HEIGHT,
	MAP_WIDTH,
	OBVODY,
	PRAHA,
	TOWNS,
	type District,
	type Region,
	type Town
} from './czech-map';

type Focus = { level: 'country' } | { level: 'kraj'; kraj: Region } | { level: 'district'; district: District };
export type ViewBox = { x: number; y: number; width: number; height: number };

const COUNTRY_TOWN_MIN_STREETS = 400;
const TOWNS_PER_KRAJ = 8;
const TOWNS_PER_DISTRICT = 12;
// Room around a region the map zooms to: a share of its larger side, plus a
// fixed margin in map units so a small region does not touch the edge.
const ZOOM_PADDING_SHARE = 0.1;
const ZOOM_PADDING_MIN = 3;

/* Where the map is: the whole country, a kraj, or a district, and the way
back. Clicking moves in, back retraces the steps. Praha opens straight to
its obvody. */
export class MapNavigation {
	// Raw, so the regions in it stay the map's own objects and compare equal.
	#focus = $state.raw<Focus>({ level: 'country' });
	#history = $state.raw<Focus[]>([]);

	get canGoBack(): boolean {
		return this.#history.length > 0;
	}

	/* The kraj in view, also when one of its districts is. */
	get kraj(): Region | null {
		if (this.#focus.level === 'kraj') return this.#focus.kraj;
		if (this.#focus.level === 'district') return krajOf(this.#focus.district);
		return null;
	}

	get district(): District | null {
		return this.#focus.level === 'district' ? this.#focus.district : null;
	}

	get inPraha(): boolean {
		return this.district === PRAHA;
	}

	/* The kraj or district in view, null over the whole country. */
	get regionInView(): Region | null {
		return this.district ?? this.kraj;
	}

	/* The districts drawn over the country, those of the kraj in view. */
	get districts(): District[] {
		const kraj = this.kraj;
		return kraj === null ? [] : districtsOf(kraj);
	}

	get obvody(): Region[] {
		return this.inPraha ? OBVODY : [];
	}

	get towns(): Town[] {
		const focus = this.#focus;
		if (focus.level === 'country') return TOWNS.filter((town) => town.streets >= COUNTRY_TOWN_MIN_STREETS);
		if (focus.level === 'kraj') return biggest(TOWNS.filter((town) => town.kraj === focus.kraj.code), TOWNS_PER_KRAJ);
		if (this.inPraha) return [];
		return biggest(TOWNS.filter((town) => town.okres === focus.district.code), TOWNS_PER_DISTRICT);
	}

	/* The regions whose names show at this level. */
	get namedRegions(): Region[] {
		if (this.#focus.level === 'country') return KRAJE;
		if (this.inPraha) return OBVODY;
		if (this.#focus.level === 'kraj') return districtsOf(this.#focus.kraj);
		return [];
	}

	get view(): ViewBox {
		const region = this.regionInView;
		return region === null ? { x: 0, y: 0, width: MAP_WIDTH, height: MAP_HEIGHT } : fit(region.bbox);
	}

	openKraj(kraj: Region): void {
		if (isPraha(kraj)) {
			this.openDistrict(PRAHA);
			return;
		}
		if (this.#focus.level === 'kraj' && this.#focus.kraj === kraj) return;
		this.#moveTo({ level: 'kraj', kraj });
	}

	openDistrict(district: District): void {
		if (this.district === district) return;
		this.#moveTo({ level: 'district', district });
	}

	openCountry(): void {
		this.#history = [];
		this.#focus = { level: 'country' };
	}

	back(): void {
		const previous = this.#history.at(-1);
		if (previous === undefined) return;
		this.#history = this.#history.slice(0, -1);
		this.#focus = previous;
	}

	/* Brings a place picked by name into view. */
	show(place: NamedPlace): void {
		if (place.kind === 'kraj') {
			const kraj = krajByCode(place.code);
			if (kraj) this.openKraj(kraj);
			return;
		}
		const district = districtOf(place);
		if (district) this.openDistrict(district);
	}

	#moveTo(focus: Focus): void {
		this.#history = [...this.#history, this.#focus];
		this.#focus = focus;
	}
}

function biggest(towns: Town[], count: number): Town[] {
	return [...towns].sort((a, b) => b.streets - a.streets).slice(0, count);
}

function fit([x0, y0, x1, y1]: Region['bbox']): ViewBox {
	const padding = Math.max(x1 - x0, y1 - y0) * ZOOM_PADDING_SHARE + ZOOM_PADDING_MIN;
	let width = x1 - x0 + 2 * padding;
	let height = y1 - y0 + 2 * padding;
	const aspect = MAP_WIDTH / MAP_HEIGHT;
	if (width / height < aspect) width = height * aspect;
	else height = width / aspect;
	return { x: (x0 + x1) / 2 - width / 2, y: (y0 + y1) / 2 - height / 2, width, height };
}
