import { describe, expect, it } from 'vitest';
import recorded from './recorded-scores.json';
import { scoreListing, scoreParts, type ScoredListing, type ScoringPreferences } from './score';

type RecordedCase = { name: string; listing: ScoredListing; preferences: ScoringPreferences; score: number };

describe('scoreListing', () => {
	it.each(recorded.cases as RecordedCase[])('gives the recorded score when $name', (recordedCase) => {
		expect(scoreListing(recordedCase.listing, recordedCase.preferences)).toBe(recordedCase.score);
	});
});

describe('scoreParts', () => {
	const full = recorded.cases.find((recordedCase) => recordedCase.name === 'a full profile adds every part') as RecordedCase;

	it('gives each weighted preference its points out of its weight', () => {
		expect(scoreParts(full.listing, full.preferences).map((part) => [part.preference, part.weight])).toEqual([
			['pricePerM2', 10],
			['disposition', 25],
			['size', 20],
			['place', 20],
			['price', 25]
		]);
	});

	it('adds up to the score', () => {
		const total = scoreParts(full.listing, full.preferences).reduce((sum, part) => sum + part.points, 0);
		expect(Math.round(total)).toBe(full.score);
	});

	it('never gives a preference more than its weight', () => {
		for (const recordedCase of recorded.cases as RecordedCase[]) {
			for (const part of scoreParts(recordedCase.listing, recordedCase.preferences)) {
				expect(part.points).toBeLessThanOrEqual(part.weight);
			}
		}
	});

	it('leaves out a preference whose listing fact is missing', () => {
		const noSize = recorded.cases.find((recordedCase) => recordedCase.name === 'size skips a listing without size') as RecordedCase;
		expect(scoreParts(noSize.listing, noSize.preferences)).toEqual([]);
	});
});
