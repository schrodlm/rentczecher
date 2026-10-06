<!-- PROTOTYPE, throwaway. Pick the search place on a map of Czechia. Click
a region to zoom in, click a town to pick it, or pick the whole region in
view. Three feels to compare: 'smooth' zooms only by clicking with slow
eased zooms and fading layers, 'spotlight' lifts the chosen region and
fades the rest away, 'free' also zooms with the wheel and pans by drag. Town dots grow with the town (its street
count stands in for population) and names appear as you zoom in. The
outlines are approximate, traced from the gazetteer's points. -->
<script lang="ts">
	import { Tween } from 'svelte/motion';
	import { cubicInOut, cubicOut } from 'svelte/easing';
	import map from './czech-map.json';
	import PlacePicker from './PlacePicker.svelte';
	import { placeLabel, type NamedPlace, type PlaceSearch } from './draft.svelte';

	let {
		place = $bindable(),
		search,
		mode = 'smooth'
	}: { place: NamedPlace | null; search: PlaceSearch; mode?: 'smooth' | 'spotlight' | 'free' } = $props();

	// svelte-ignore state_referenced_locally
	const free = mode === 'free';

	type Region = { kind: string; code: number; name: string; path: string; bbox: number[]; label: number[]; kraj?: number };
	type Obec = { code: number; name: string; okres: number | null; kraj: number; x: number; y: number; streets: number };

	const kraje = map.kraje as Region[];
	const okresy = map.okresy as Region[];
	const obvody = map.obvody as Region[];
	const obce = map.obce as Obec[];
	const PRAHA = 554782;
	const prahaRegion = okresy.find((o) => o.kind === 'obec' && o.code === PRAHA)!;

	type Focus = { level: 'country' } | { level: 'kraj'; kraj: Region } | { level: 'okres'; okres: Region };
	// Raw state, so the regions inside stay comparable to the map's own.
	let focus = $state.raw<Focus>({ level: 'country' });

	const full = [0, 0, map.width, map.height];
	// svelte-ignore state_referenced_locally
	const view = new Tween(full, free ? { duration: 450, easing: cubicOut } : { duration: 800, easing: cubicInOut });
	let svg: SVGSVGElement;

	function fit(bbox: number[]): number[] {
		const [x0, y0, x1, y1] = bbox;
		const pad = Math.max(x1 - x0, y1 - y0) * 0.1 + 3;
		let w = x1 - x0 + 2 * pad;
		let h = y1 - y0 + 2 * pad;
		const aspect = map.width / map.height;
		if (w / h < aspect) w = h * aspect;
		else h = w / aspect;
		return [(x0 + x1) / 2 - w / 2, (y0 + y1) / 2 - h / 2, w, h];
	}

	function focusCountry(): void {
		previous = [];
		focus = { level: 'country' };
		view.target = full;
	}

	function focusKraj(kraj: Region): void {
		if (kraj.code === 19) return focusOkres(prahaRegion);
		if (focus.level === 'kraj' && focus.kraj === kraj) return;
		remember();
		focus = { level: 'kraj', kraj };
		view.target = fit(kraj.bbox);
	}

	function focusOkres(okres: Region): void {
		if (focus.level === 'okres' && focus.okres === okres) return;
		remember();
		focus = { level: 'okres', okres };
		view.target = fit(okres.bbox);
	}

	const krajOfFocus = $derived.by(() => {
		if (focus.level === 'kraj') return focus.kraj;
		if (focus.level === 'okres') {
			const krajCode = focus.okres.kraj;
			return kraje.find((k) => k.code === krajCode) ?? null;
		}
		return null;
	});
	const isPraha = $derived(focus.level === 'okres' && focus.okres === prahaRegion);

	// Praha is its own kraj, enclosed by Středočeský, so it joins the okresy
	// shown there instead of leaving a hole.
	const STREDOCESKY = 27;
	function okresyOf(krajCode: number | undefined): Region[] {
		const own = okresy.filter((o) => o.kraj === krajCode);
		return krajCode === STREDOCESKY ? [...own, prahaRegion] : own;
	}

	// Up goes back to where the map was, so Praha opened from Středočeský
	// returns there.
	let previous = $state.raw<Focus[]>([]);

	function up(): void {
		const last = previous.at(-1);
		if (!last) return;
		previous = previous.slice(0, -1);
		focus = last;
		view.target = last.level === 'country' ? full : fit(last.level === 'kraj' ? last.kraj.bbox : last.okres.bbox);
	}

	function remember(): void {
		previous = [...previous, focus];
	}

	function named(kind: string, code: number): NamedPlace {
		if (kind === 'kraj') return { kind, code, name: kraje.find((k) => k.code === code)!.name, obec: null, okres: null };
		if (kind === 'okres') return { kind, code, name: okresy.find((o) => o.kind === 'okres' && o.code === code)!.name, obec: null, okres: null };
		if (kind === 'obvod') return { kind, code, name: obvody.find((o) => o.code === code)!.name, obec: 'Praha', okres: null };
		const obec = obce.find((o) => o.code === code);
		const okres = okresy.find((o) => o.kind === 'okres' && o.code === obec?.okres);
		return { kind: 'obec', code, name: code === PRAHA ? 'Praha' : obec!.name, obec: null, okres: okres?.name ?? null };
	}

	const isPicked = (kind: string, code: number) => place !== null && place.kind === kind && place.code === code;

	function pick(kind: string, code: number): void {
		place = isPicked(kind, code) ? null : named(kind, code);
	}

	function pickFromSearch(found: NamedPlace): void {
		place = found;
		show(found);
	}

	// Bring a picked place into view.
	function show(found: NamedPlace): void {
		if (found.kind === 'kraj') return focusKraj(kraje.find((k) => k.code === found.code)!);
		if (found.kind === 'okres') return focusOkres(okresy.find((o) => o.kind === 'okres' && o.code === found.code)!);
		if (found.obec === 'Praha' || (found.kind === 'obec' && found.code === PRAHA)) return focusOkres(prahaRegion);
		const obec =
			found.kind === 'obec'
				? obce.find((o) => o.code === found.code)
				: obce.find((o) => o.name === found.obec && okresy.find((k) => k.code === o.okres)?.name === found.okres);
		const okres = obec && okresy.find((o) => o.kind === 'okres' && o.code === obec.okres);
		if (okres) focusOkres(okres);
	}

	const wholeTarget = $derived.by((): { kind: string; code: number; name: string } | null => {
		if (focus.level === 'kraj') return { kind: 'kraj', code: focus.kraj.code, name: focus.kraj.name };
		if (focus.level === 'okres') return { kind: focus.okres.kind, code: focus.okres.code, name: focus.okres.name };
		return null;
	});

	const pickedRegion = $derived.by((): Region | null => {
		if (place === null) return null;
		const picked = place;
		if (picked.kind === 'kraj') return kraje.find((k) => k.code === picked.code) ?? null;
		if (picked.kind === 'okres') return okresy.find((o) => o.kind === 'okres' && o.code === picked.code) ?? null;
		if (picked.kind === 'obvod') return obvody.find((o) => o.code === picked.code) ?? null;
		if (picked.kind === 'obec' && picked.code === PRAHA) return prahaRegion;
		return null;
	});

	// Zoom and pan. A drag pans, and a press that barely moves stays a click.
	const vw = $derived(view.current[2]);
	// Big towns show early, villages only when zoomed in close.
	const minStreetsForDot = $derived(vw > 600 ? 400 : vw > 300 ? 40 : vw > 150 ? 4 : 0);
	const showTowns = $derived(vw < 420);
	let drag: { x: number; y: number; view: number[]; moved: boolean } | null = null;
	let suppressClick = false;

	function onwheel(event: WheelEvent): void {
		event.preventDefault();
		const [x, y, w, h] = view.current;
		const rect = svg.getBoundingClientRect();
		const fx = (event.clientX - rect.left) / rect.width;
		const fy = (event.clientY - rect.top) / rect.height;
		const factor = Math.exp(event.deltaY * 0.0015);
		const nw = Math.min(map.width * 1.1, Math.max(8, w * factor));
		const nh = (nw * h) / w;
		view.set([x + fx * w - fx * nw, y + fy * h - fy * nh, nw, nh], { duration: 0 });
	}

	function onpointerdown(event: PointerEvent): void {
		drag = { x: event.clientX, y: event.clientY, view: [...view.current], moved: false };
	}

	function onpointermove(event: PointerEvent): void {
		if (!drag) return;
		const dx = event.clientX - drag.x;
		const dy = event.clientY - drag.y;
		if (!drag.moved && Math.hypot(dx, dy) < 4) return;
		if (!drag.moved) svg.setPointerCapture(event.pointerId);
		drag.moved = true;
		const k = drag.view[2] / svg.clientWidth;
		const [x, y, w, h] = drag.view;
		view.set([x - dx * k, y - dy * k, w, h], { duration: 0 });
	}

	function onpointerup(): void {
		suppressClick = drag?.moved ?? false;
		drag = null;
	}

	function onRegionClick(action: () => void): void {
		if (suppressClick) {
			suppressClick = false;
			return;
		}
		action();
	}

	function radius(obec: Obec, width = vw): number {
		return (width / 260) * (0.55 + Math.log10(obec.streets + 1) * 0.55);
	}

	// Fewer names when zoomed out: only towns with enough streets for the zoom.
	const minStreetsForName = $derived(vw > 600 ? 600 : vw > 300 ? 150 : vw > 150 ? 40 : vw > 70 ? 15 : vw > 35 ? 3 : 0);

	// Without free zoom: the biggest cities across the country, the few
	// biggest towns of a kraj, and the main towns of an okres.
	const biggest = (towns: Obec[], count: number) => [...towns].sort((a, b) => b.streets - a.streets).slice(0, count);
	const levelTowns = $derived.by(() => {
		if (focus.level === 'country') return obce.filter((o) => o.code !== PRAHA && o.streets >= 400);
		if (focus.level === 'kraj') {
			const krajCode = focus.kraj.code;
			return biggest(obce.filter((o) => o.kraj === krajCode), 8);
		}
		if (isPraha) return [];
		const okresCode = focus.okres.code;
		return biggest(obce.filter((o) => o.okres === okresCode), 12);
	});

	const visibleTowns = $derived.by(() => {
		if (!free) return levelTowns;
		const [x, y, w, h] = view.current;
		return obce.filter(
			(o) => o.code !== PRAHA && o.streets >= minStreetsForDot && o.x >= x && o.x <= x + w && o.y >= y && o.y <= y + h
		);
	});
	const namedTowns = $derived(
		!free ? levelTowns : visibleTowns.filter((o) => o.streets >= minStreetsForName).sort((a, b) => b.streets - a.streets).slice(0, 35)
	);

	const showObvody = $derived(isPraha || (free && vw < 80 && view.current[0] < prahaRegion.bbox[2] && view.current[0] + vw > prahaRegion.bbox[0]));

	// Labels are placed so none covers another or a town's dot: region names
	// first, nudged up or down when two collide, then town names biggest
	// first, each in the first free spot around its dot. A name with no free
	// spot is left out, and its dot still names itself on hover.
	type Box = { x0: number; y0: number; x1: number; y1: number };
	type Anchor = 'start' | 'middle' | 'end';
	const overlaps = (a: Box, b: Box) => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
	// Bold system-ui runs about 0.6 em per character.
	function textBox(x: number, y: number, text: string, size: number, anchor: Anchor): Box {
		const width = text.length * size * 0.6;
		const x0 = anchor === 'start' ? x : anchor === 'end' ? x - width : x - width / 2;
		return { x0, y0: y - size * 0.6, x1: x0 + width, y1: y + size * 0.6 };
	}
	const shortName = (region: Region) => region.name.replace(' kraj', '').replace('Kraj ', '');

	const labels = $derived.by(() => {
		// Laid out for where the zoom lands, so labels hold still while it runs.
		const width = free ? vw : view.target[2];
		const regionSize = width / 60;
		const townSize = width / 75;
		const gap = width / 200;
		const dots = new Map<number, Box>();
		for (const o of visibleTowns) {
			const r = radius(o, width);
			dots.set(o.code, { x0: o.x - r, y0: o.y - r, x1: o.x + r, y1: o.y + r });
		}
		const taken: Box[] = [...dots.values()];

		const regions = regionLabels.map((region) => {
			const [x, y] = region.label;
			const text = shortName(region);
			const spot =
				[0, 1.2, -1.2, 2.4, -2.4]
					.map((shift) => ({ y: y + shift * regionSize, box: textBox(x, y + shift * regionSize, text, regionSize, 'middle') }))
					.find((c) => !taken.some((b) => overlaps(b, c.box))) ?? { y, box: textBox(x, y, text, regionSize, 'middle') };
			taken.push(spot.box);
			return { region, text, x, y: spot.y };
		});

		const towns: { obec: Obec; x: number; y: number; anchor: Anchor }[] = [];
		for (const obec of [...namedTowns].sort((a, b) => b.streets - a.streets)) {
			const r = radius(obec, width);
			const ownDot = dots.get(obec.code);
			const around: { x: number; y: number; anchor: Anchor }[] = [
				{ x: obec.x, y: obec.y - r - gap - townSize * 0.6, anchor: 'middle' },
				{ x: obec.x, y: obec.y + r + gap + townSize * 0.6, anchor: 'middle' },
				{ x: obec.x + r + gap, y: obec.y, anchor: 'start' },
				{ x: obec.x - r - gap, y: obec.y, anchor: 'end' }
			];
			const spot = around.find((c) => {
				const box = textBox(c.x, c.y, obec.name, townSize, c.anchor);
				return !taken.some((b) => b !== ownDot && overlaps(b, box));
			});
			if (!spot) continue;
			taken.push(textBox(spot.x, spot.y, obec.name, townSize, spot.anchor));
			towns.push({ obec, ...spot });
		}
		return { regions, towns };
	});

	const regionLabels = $derived.by((): Region[] => {
		if (!free) {
			if (focus.level === 'country') return kraje;
			if (isPraha) return obvody;
			if (focus.level === 'kraj') {
				const krajCode = focus.kraj.code;
				return okresyOf(krajCode);
			}
			return [];
		}
		if (vw > 500) return kraje;
		if (showObvody) return obvody;
		// An okres is mostly named after its town, so its label gives way once
		// that town is named.
		if (vw > 120) return okresy.filter((o) => o.kind === 'okres' && !namedTowns.some((t) => t.name === o.name));
		return [];
	});
</script>

<div class="mappicker">
	<div class="topline">
		<div class="search"><PlacePicker search={(q) => search(q, null)} placeholder="Search a place by name: a town, part of town, street..." onpick={pickFromSearch} /></div>
		<div class="picked">
			{#if place}
				<span class="picked__label">Searching in</span>
				<span class="chip">
					<button type="button" class="chip__name" onclick={() => show(place!)}>{placeLabel(place)}</button>
					<button type="button" class="chip__x" aria-label="Clear" onclick={() => (place = null)}>×</button>
				</span>
			{:else}
				<span class="picked__label">No place picked yet</span>
			{/if}
		</div>
	</div>

	<div class="toolbar">
		<button type="button" class="back" disabled={previous.length === 0} onclick={up} aria-label="Up one level">←</button>
		<nav class="crumbs">
			<button type="button" onclick={focusCountry} class:current={focus.level === 'country'}>Česko</button>
			{#if krajOfFocus}
				<span>›</span>
				<button type="button" onclick={() => focusKraj(krajOfFocus!)} class:current={focus.level === 'kraj' || isPraha}>{krajOfFocus.name}</button>
			{/if}
			{#if focus.level === 'okres' && !isPraha}<span>›</span><span class="current">{focus.okres.name}</span>{/if}
		</nav>
		<span class="spacer"></span>
		{#if wholeTarget}
			<button type="button" class="whole" class:on={isPicked(wholeTarget.kind, wholeTarget.code)} onclick={() => pick(wholeTarget!.kind, wholeTarget!.code)}>
				{isPicked(wholeTarget.kind, wholeTarget.code) ? `✓ Searching all of ${wholeTarget.name}` : `Search all of ${wholeTarget.name}`}
			</button>
		{/if}
	</div>

	<svg
		bind:this={svg}
		class="mode-{mode}"
		viewBox={view.current.join(' ')}
		role="application"
		aria-label="Map of Czechia"
		onwheel={free ? onwheel : undefined}
		onpointerdown={free ? onpointerdown : undefined}
		onpointermove={free ? onpointermove : undefined}
		onpointerup={free ? onpointerup : undefined}
		onpointercancel={free ? onpointerup : undefined}
	>
		<defs>
			<filter id="lift" x="-10%" y="-10%" width="120%" height="120%">
				<feDropShadow dx="0" dy="1.5" stdDeviation="2.5" flood-color="#000" flood-opacity="0.28" />
			</filter>
		</defs>
		{#each kraje as kraj (kraj.code)}
			<path
				d={kraj.path}
				class="kraj"
				class:dim={focus.level !== 'country' && krajOfFocus !== kraj}
				class:focused={focus.level !== 'country' && krajOfFocus === kraj}
				role="button"
				tabindex="-1"
				onclick={() => onRegionClick(() => focusKraj(kraj))}
				onkeydown={() => {}}
			><title>{kraj.name}</title></path>
		{/each}

		{#if free ? vw < 500 : focus.level !== 'country'}
			{#each free ? okresy : okresyOf(krajOfFocus?.code) as okres (okres.kind + okres.code)}
				<path
					d={okres.path}
					class="okres enter"
					pathLength="1"
					class:dim={focus.level === 'okres' && focus.okres !== okres}
					class:focused={focus.level === 'okres' && focus.okres === okres}
					role="button"
					tabindex="-1"
					onclick={() => onRegionClick(() => focusOkres(okres))}
					onkeydown={() => {}}
				><title>{okres.name}</title></path>
			{/each}
		{/if}

		{#if showObvody}
			{#each obvody as obvod (obvod.code)}
				<path
					d={obvod.path}
					class="obvod enter"
					class:picked={isPicked('obvod', obvod.code)}
					role="button"
					tabindex="-1"
					onclick={() => onRegionClick(() => pick('obvod', obvod.code))}
					onkeydown={() => {}}
				><title>{obvod.name}</title></path>
			{/each}
		{/if}

		{#if pickedRegion}
			<path d={pickedRegion.path} class="picked-region" />
		{/if}

		{#each labels.regions as placed (focus.level + placed.region.kind + placed.region.code)}
			<text x={placed.x} y={placed.y} font-size={vw / 60} class="label region-label enter-late">{placed.text}</text>
		{/each}

		{#each visibleTowns as obec (focus.level + obec.code)}
			<circle
				cx={obec.x}
				cy={obec.y}
				r={radius(obec)}
				class="town enter-late"
				class:picked={isPicked('obec', obec.code)}
				role="button"
				tabindex="-1"
				onclick={() => onRegionClick(() => pick('obec', obec.code))}
				onkeydown={() => {}}
			><title>{obec.name}</title></circle>
		{/each}

		{#each labels.towns as placed (focus.level + placed.obec.code)}
			<text x={placed.x} y={placed.y} text-anchor={placed.anchor} font-size={vw / 75} class="label town-label enter-late">{placed.obec.name}</text>
		{/each}
	</svg>

	<p class="hint">
		{#if free}Click a region to zoom in, or scroll to zoom and drag to move.{:else}Click a region to zoom in.{/if}
		{#if free ? showTowns : focus.level === 'okres' && !isPraha}Click a town to search there. For a smaller village, search it by name.{/if}
		{#if showObvody}Click a Praha district to search there.{/if}
	</p>
</div>

<style>
	.mappicker { display: flex; flex-direction: column; gap: var(--space-2); }
	.topline { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); align-items: center; }
	.search :global(input) { padding: var(--space-2) var(--space-3); border: 1px solid var(--color-line); border-radius: var(--radius-full); background: var(--color-card); color: inherit; font-size: 0.9375rem; }
	.picked { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
	.picked__label { color: var(--color-bronze); font-size: 0.8125rem; }
	.chip { display: inline-flex; align-items: center; background: var(--color-card); border: 1px solid var(--color-amber); border-radius: var(--radius-full); padding: 0 var(--space-1) 0 var(--space-3); font-size: 0.875rem; font-weight: 600; }
	.chip__name, .chip__x { background: none; border: none; color: inherit; cursor: pointer; padding: var(--space-1); }
	.chip__x { color: var(--color-bronze); font-size: 1rem; line-height: 1; }
	.toolbar { display: flex; align-items: center; gap: var(--space-2); min-height: 2rem; }
	.back { width: 2rem; height: 2rem; border-radius: var(--radius-full); border: 1px solid var(--color-line); background: var(--color-card); color: inherit; cursor: pointer; font-size: 1rem; }
	.back:disabled { opacity: 0.35; cursor: default; }
	.crumbs { display: flex; gap: var(--space-1); align-items: center; font-size: 0.875rem; color: var(--color-bronze); }
	.crumbs button { background: none; border: none; color: var(--color-bronze); cursor: pointer; padding: 0; text-decoration: underline; }
	.crumbs .current { color: var(--color-ink); font-weight: 600; text-decoration: none; }
	.spacer { flex: 1; }
	.whole { border: 1px solid var(--color-olive); background: var(--color-card); color: var(--color-olive); border-radius: var(--radius-full); padding: var(--space-1) var(--space-3); cursor: pointer; font-weight: 600; font-size: 0.8125rem; }
	.whole.on { background: var(--color-olive); color: var(--color-ground); }
	svg { width: 100%; aspect-ratio: 900 / 522; background: var(--color-ground); border: 1px solid var(--color-line); border-radius: var(--radius-md); touch-action: none; cursor: grab; user-select: none; }
	svg:active { cursor: grabbing; }
	path { stroke: var(--color-ground); stroke-width: 0.8; vector-effect: non-scaling-stroke; cursor: pointer; transition: fill 120ms; }
	.kraj { fill: var(--color-line); }
	.kraj:hover { fill: #e0d2b8; }
	.kraj.dim { fill: #efe8db; }
	.okres { fill: #e2d6bf; }
	.okres:hover { fill: #d8c9ad; }
	.okres.dim { fill: #ece3d3; }
	.obvod { fill: #e2d6bf; }
	.obvod:hover { fill: #d4c3a2; }
	.obvod.picked, .picked-region { fill: var(--color-amber); fill-opacity: 0.7; }
	.picked-region { pointer-events: none; stroke: var(--color-bronze); stroke-width: 1.5; }
	.town { fill: var(--color-bronze); fill-opacity: 0.6; stroke: var(--color-ground); stroke-width: 0.5; vector-effect: non-scaling-stroke; cursor: pointer; }
	.town:hover { fill-opacity: 1; }
	.town.picked { fill: var(--color-amber); fill-opacity: 1; stroke: var(--color-ink); stroke-width: 1.5; }
	.label { pointer-events: none; paint-order: stroke; stroke: var(--color-ground); stroke-width: 3px; stroke-linejoin: round; vector-effect: non-scaling-stroke; fill: var(--color-ink); }
	.region-label { text-anchor: middle; dominant-baseline: middle; font-weight: 700; fill-opacity: 0.6; }
	.town-label { font-weight: 600; dominant-baseline: middle; }
	.hint { margin: 0; color: var(--color-bronze); font-size: 0.8125rem; }

	/* Click and fade, and spotlight: no grab cursor, layers fade in once the
	zoom has mostly landed. CSS animations only, since the app's content
	policy may refuse the style tags script-driven transitions create. */
	svg.mode-smooth, svg.mode-spotlight { cursor: default; }
	svg.mode-smooth path, svg.mode-spotlight path { transition: fill 200ms, opacity 600ms ease, fill-opacity 600ms ease; }
	svg:not(.mode-free) .enter { animation: fade-in 500ms ease 250ms both; }
	svg:not(.mode-free) .enter-late { animation: fade-in 450ms ease 650ms both; }
	@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

	/* Spotlight: the region in focus lifts, the rest fades back, and okres
	borders draw themselves in. */
	svg.mode-spotlight .kraj.dim { opacity: 0.18; }
	svg.mode-spotlight .kraj.focused { filter: url(#lift); fill: #f3ecdf; }
	svg.mode-spotlight .okres.dim { opacity: 0.35; }
	svg.mode-spotlight .okres.focused { filter: url(#lift); }
	svg.mode-spotlight .okres.enter { stroke: var(--color-bronze); stroke-opacity: 0.55; animation: fade-in 400ms ease 200ms both, draw 900ms ease 250ms both; }
	@keyframes draw { from { stroke-dasharray: 0 1; } to { stroke-dasharray: 1 0; } }
</style>
