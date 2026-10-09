/* PROTOTYPE, throwaway. Weights set directly on a split bar: the preferences
that are on share 100, a divider trades weight between its two neighbours,
and switching a preference on or off rescales the rest in proportion. */

import { WISHES, isReady, type Wish, type WishSettings } from '$lib/scoring/wishes';
import type { NamedPlace } from '$lib/api/client';
import { formatArea, formatPrice } from '$lib/format';

export type { Wish };

export const MIN_SHARE = 5;

export const TITLE: Record<Wish, string> = {
	price: 'Dobrá cena',
	size: 'Správná velikost',
	land: 'Dost pozemku',
	layout: 'Dispozice',
	place: 'Místo'
};

export const SHORT: Record<Wish, string> = {
	price: 'Cena',
	size: 'Velikost',
	land: 'Pozemek',
	layout: 'Dispozice',
	place: 'Místo'
};

export const ICON: Record<Wish, string> = {
	price: 'Kč',
	size: 'm²',
	land: '▱',
	layout: '⊞',
	place: '⌖'
};

export class SplitState {
	weights = $state<Record<Wish, number>>({ price: 45, size: 20, land: 0, layout: 25, place: 10 });
	settings = $state<WishSettings>({
		max_good_price: 22000,
		ideal_size_m2: 70,
		ideal_land_m2: null,
		preferred_dispositions: ['2+kk', '2+1'],
		preferred_places: [
			{ kind: 'mestska_cast', code: 500186, name: 'Praha 7', obec: 'Praha', okres: null } as NamedPlace
		]
	});
	available: readonly Wish[] = ['price', 'size', 'layout', 'place'];

	on = $derived(this.available.filter((wish) => this.weights[wish] > 0));

	ready(wish: Wish): boolean {
		return isReady(wish, this.settings);
	}

	/* Move the divider after the index-th preference that is on by delta
	percentage points, never shrinking either neighbour below the minimum. */
	moveDivider(index: number, delta: number): void {
		const left = this.on[index];
		const right = this.on[index + 1];
		const pair = this.weights[left] + this.weights[right];
		const newLeft = Math.min(pair - MIN_SHARE, Math.max(MIN_SHARE, Math.round(this.weights[left] + delta)));
		this.weights = { ...this.weights, [left]: newLeft, [right]: pair - newLeft };
	}

	/* Drags a divider with the pointer, measured from where the drag began so
rounding never piles up. */
	drag(index: number, event: PointerEvent, bar: HTMLElement): void {
		const handle = event.currentTarget as HTMLElement;
		handle.setPointerCapture(event.pointerId);
		const left = this.on[index];
		const startWeight = this.weights[left];
		const startX = event.clientX;
		const width = bar.getBoundingClientRect().width;
		const move = (moved: PointerEvent) => {
			const delta = ((moved.clientX - startX) / width) * 100;
			this.moveDivider(index, startWeight + delta - this.weights[left]);
		};
		const stop = () => {
			handle.removeEventListener('pointermove', move);
			handle.removeEventListener('pointerup', stop);
			handle.removeEventListener('pointercancel', stop);
		};
		handle.addEventListener('pointermove', move);
		handle.addEventListener('pointerup', stop);
		handle.addEventListener('pointercancel', stop);
	}

	/* Arrow keys nudge a focused divider by one point, shift by five. */
	nudge(index: number, event: KeyboardEvent): void {
		const step = event.shiftKey ? 5 : 1;
		if (event.key === 'ArrowLeft') this.moveDivider(index, -step);
		else if (event.key === 'ArrowRight') this.moveDivider(index, step);
		else return;
		event.preventDefault();
	}

	toggle(wish: Wish): void {
		const next = { ...this.weights };
		if (next[wish] > 0) {
			next[wish] = 0;
		} else {
			if (!this.ready(wish)) return;
			const count = this.on.length + 1;
			next[wish] = Math.round(100 / count);
		}
		this.weights = rescale(next, wish, this.available);
	}
}

/* Scales every other preference that is on so all add up to 100 again,
keeping how they compare. */
function rescale(weights: Record<Wish, number>, fixed: Wish, available: readonly Wish[]): Record<Wish, number> {
	const others = available.filter((wish) => wish !== fixed && weights[wish] > 0);
	const room = 100 - weights[fixed];
	const othersTotal = others.reduce((sum, wish) => sum + weights[wish], 0);
	const result = { ...weights };
	if (others.length === 0) {
		if (weights[fixed] > 0) result[fixed] = 100;
		return result;
	}
	let given = 0;
	others.forEach((wish, index) => {
		const share =
			index === others.length - 1
				? room - given
				: Math.max(MIN_SHARE, Math.round((weights[wish] / othersTotal) * room));
		result[wish] = share;
		given += share;
	});
	return result;
}

export const ALL_WISHES = WISHES;

export function rule(split: SplitState, wish: Wish): string {
	const s = split.settings;
	if (wish === 'price')
		return s.max_good_price === null
			? 'Nejdřív nastavte dobrou cenu.'
			: `Plný počet bodů do ${formatPrice(s.max_good_price)}, od ${formatPrice(2 * s.max_good_price)} žádné.`;
	if (wish === 'size')
		return s.ideal_size_m2 === null
			? 'Nejdřív nastavte ideální velikost.'
			: `Plný počet bodů od ${formatArea(s.ideal_size_m2)}, polovina při ${formatArea(Math.round(s.ideal_size_m2 / 2))}.`;
	if (wish === 'land') return 'Plný počet bodů od ideálního pozemku.';
	if (wish === 'layout') return 'Kterákoli z vybraných dispozic dostane plný počet bodů. Ostatní 10.';
	return 'Inzerát v kterémkoli z míst dostane plný počet bodů. Jinde 20.';
}
