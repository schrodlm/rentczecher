import type { Weights, Wish } from './wishes';

/* The fewest points a preference on the bar holds, so every segment stays
wide enough to grab. */
export const MIN_WEIGHT = 5;

const NO_WEIGHTS: Weights = { price: 0, size: 0, land: 0, layout: 0, place: 0 };

/* Moves the divider between two neighbouring preferences on the bar: the
left one gains what the right one loses. */
export function moveDivider(weights: Weights, left: Wish, right: Wish, delta: number): Weights {
	const pair = weights[left] + weights[right];
	const moved = Math.min(pair - MIN_WEIGHT, Math.max(MIN_WEIGHT, Math.round(weights[left] + delta)));
	return { ...weights, [left]: moved, [right]: pair - moved };
}

/* Gives a preference an equal share of the bar, taken from the counting
ones in proportion. */
export function switchOn(weights: Weights, wish: Wish, counting: readonly Wish[]): Weights {
	const others = counting.filter((other) => other !== wish);
	const share = Math.round(100 / (others.length + 1));
	const shared = { ...scaledTo(weights, others, 100 - share), [wish]: share };
	return liftedToMinimum(shared, [...others, wish]);
}

/* Hands a preference's share back to the counting ones in proportion. */
export function switchOff(weights: Weights, wish: Wish, counting: readonly Wish[]): Weights {
	const others = counting.filter((other) => other !== wish);
	return scaledTo(weights, others, 100);
}

/* The counting preferences' weights scaled to add up to 100, every other
preference at 0. A preference stops counting when its preferred value is
cleared, and the rest grow to fill its share. */
export function settled(weights: Weights, counting: readonly Wish[]): Weights {
	return scaledTo(weights, counting, 100);
}

/* Raises every preference below the minimum to it, taking the points from
the heaviest one. */
function liftedToMinimum(weights: Weights, among: readonly Wish[]): Weights {
	const lifted = { ...weights };
	for (const wish of among) {
		const missing = MIN_WEIGHT - lifted[wish];
		if (missing <= 0) continue;
		const heaviest = among.reduce((heavier, other) => (lifted[other] > lifted[heavier] ? other : heavier));
		lifted[heaviest] -= missing;
		lifted[wish] = MIN_WEIGHT;
	}
	return lifted;
}

/* Shares a whole-number total between some preferences in proportion to
their weights, equally when they all weigh nothing. Rounding leftovers go to
the largest remainders, ties to the earlier preference. */
function scaledTo(weights: Weights, among: readonly Wish[], total: number): Weights {
	const scaled = { ...NO_WEIGHTS };
	if (among.length === 0) return scaled;
	const sum = among.reduce((running, wish) => running + weights[wish], 0);
	const exact = among.map((wish) => (sum === 0 ? total / among.length : (weights[wish] * total) / sum));
	const whole = exact.map(Math.floor);
	let left = total - whole.reduce((running, weight) => running + weight, 0);
	const byRemainder = among
		.map((_wish, index) => index)
		.sort((a, b) => exact[b] - whole[b] - (exact[a] - whole[a]));
	for (const index of byRemainder) {
		if (left === 0) break;
		whole[index] += 1;
		left -= 1;
	}
	for (const [index, wish] of among.entries()) scaled[wish] = whole[index];
	return scaled;
}
