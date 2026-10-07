export type Box = { x0: number; y0: number; x1: number; y1: number };
export type Anchor = 'start' | 'middle' | 'end';

export type RegionLabel = { key: string; text: string; x: number; y: number };
export type TownLabel = { key: string; text: string; x: number; y: number; radius: number; streets: number };
export type PlacedLabel = { key: string; text: string; x: number; y: number; anchor: Anchor };

export type LabelSizes = { region: number; town: number; gap: number };

// How far a region name may move from its spot, in heights of its own text.
const REGION_SHIFTS = [0, 1.2, -1.2, 2.4, -2.4];
// Bold system-ui runs about 0.6 em per character.
const EM_PER_CHARACTER = 0.6;

/* Places every name so none covers another or a town's dot. Region names go
first, each moved up or down when it would collide, and keep their spot when
nothing is free. Town names follow, biggest town first, each in the first
free spot around its dot: above, below, right, then left. A town with no free
spot goes unnamed. */
export function placeLabels(
	regions: RegionLabel[],
	towns: TownLabel[],
	sizes: LabelSizes
): { regions: PlacedLabel[]; towns: PlacedLabel[] } {
	const dots = new Map(towns.map((town) => [town.key, dotBox(town)]));
	const taken: Box[] = [...dots.values()];

	const placedRegions = regions.map((region) => {
		const spots = REGION_SHIFTS.map((shift) => region.y + shift * sizes.region);
		const y =
			spots.find((candidate) => isFree(textBox(region.x, candidate, region.text, sizes.region, 'middle'), taken)) ??
			region.y;
		taken.push(textBox(region.x, y, region.text, sizes.region, 'middle'));
		return { key: region.key, text: region.text, x: region.x, y, anchor: 'middle' as const };
	});

	const placedTowns: PlacedLabel[] = [];
	for (const town of [...towns].sort((a, b) => b.streets - a.streets)) {
		const ownDot = dots.get(town.key);
		const others = taken.filter((box) => box !== ownDot);
		const spot = spotsAround(town, sizes).find((candidate) =>
			isFree(textBox(candidate.x, candidate.y, town.text, sizes.town, candidate.anchor), others)
		);
		if (spot === undefined) continue;
		taken.push(textBox(spot.x, spot.y, town.text, sizes.town, spot.anchor));
		placedTowns.push({ key: town.key, text: town.text, ...spot });
	}

	return { regions: placedRegions, towns: placedTowns };
}

function spotsAround(town: TownLabel, sizes: LabelSizes): { x: number; y: number; anchor: Anchor }[] {
	const clearance = town.radius + sizes.gap;
	const halfHeight = sizes.town * EM_PER_CHARACTER;
	return [
		{ x: town.x, y: town.y - clearance - halfHeight, anchor: 'middle' },
		{ x: town.x, y: town.y + clearance + halfHeight, anchor: 'middle' },
		{ x: town.x + clearance, y: town.y, anchor: 'start' },
		{ x: town.x - clearance, y: town.y, anchor: 'end' }
	];
}

function dotBox(town: TownLabel): Box {
	return { x0: town.x - town.radius, y0: town.y - town.radius, x1: town.x + town.radius, y1: town.y + town.radius };
}

/* The box a text takes when drawn at x, y, its middle on y. */
export function textBox(x: number, y: number, text: string, size: number, anchor: Anchor): Box {
	const width = text.length * size * EM_PER_CHARACTER;
	const x0 = anchor === 'start' ? x : anchor === 'end' ? x - width : x - width / 2;
	return { x0, y0: y - size * EM_PER_CHARACTER, x1: x0 + width, y1: y + size * EM_PER_CHARACTER };
}

function isFree(box: Box, taken: Box[]): boolean {
	return !taken.some((other) => box.x0 < other.x1 && other.x0 < box.x1 && box.y0 < other.y1 && other.y0 < box.y1);
}
