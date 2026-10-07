import { describe, expect, it } from 'vitest';
import recorded from './recorded-scores.json';
import { scoreListing, type ScoredListing, type ScoringPreferences } from './score';

type RecordedCase = { name: string; listing: ScoredListing; preferences: ScoringPreferences; score: number };

describe('scoreListing', () => {
	it.each(recorded.cases as RecordedCase[])('gives the recorded score when $name', (recordedCase) => {
		expect(scoreListing(recordedCase.listing, recordedCase.preferences)).toBe(recordedCase.score);
	});
});
