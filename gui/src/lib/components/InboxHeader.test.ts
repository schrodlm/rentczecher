import { describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';
import InboxHeader from './InboxHeader.svelte';

describe('InboxHeader', () => {
	test('shows a not-yet-run label with no prior run', async () => {
		const { getByText } = await renderWithTranslator(InboxHeader, {
			health: [],
			runState: { status: 'idle' },
			lastFinishedAt: null,
			triggerError: null,
			onrun: () => {}
		});
		expect(getByText('Ještě nespuštěno')).toBeInTheDocument();
	});

	test('disables the run button and shows a running label while a run is in progress', async () => {
		const { getByRole } = await renderWithTranslator(InboxHeader, {
			health: [],
			runState: { status: 'running', profileId: 'a', scrapersDone: [] },
			lastFinishedAt: null,
			triggerError: null,
			onrun: () => {}
		});
		const button = getByRole('button', { name: 'Scan běží...' });
		expect(button).toBeDisabled();
	});

	test('counts finished scrapers as run_progress events arrive', async () => {
		const { getByText } = await renderWithTranslator(InboxHeader, {
			health: [],
			runState: {
				status: 'running',
				profileId: 'a',
				scrapersDone: [
					{ run_id: 'r1', profile_id: 'a', scraper: 'sreality', status: 'ok', listing_count: 10 }
				]
			},
			lastFinishedAt: null,
			triggerError: null,
			onrun: () => {}
		});
		expect(getByText('Hotovo 1 portál')).toBeInTheDocument();
	});

	test('calls onrun when the run button is clicked while idle', async () => {
		const onrun = vi.fn();
		const { getByRole } = await renderWithTranslator(InboxHeader, {
			health: [],
			runState: { status: 'idle' },
			lastFinishedAt: null,
			triggerError: null,
			onrun
		});
		(getByRole('button', { name: 'Spustit scan' }) as HTMLElement).click();
		expect(onrun).toHaveBeenCalledOnce();
	});

	test('renders one health dot per portal', async () => {
		const { getByLabelText } = await renderWithTranslator(InboxHeader, {
			health: [
				{ portal: 'sreality', status: 'ok', error: null, listing_count: 10, checked_at: '' },
				{ portal: 'remax', status: 'broken', error: 'boom', listing_count: 0, checked_at: '' }
			],
			runState: { status: 'idle' },
			lastFinishedAt: null,
			triggerError: null,
			onrun: () => {}
		});
		expect(getByLabelText('sreality: v pořádku')).toBeInTheDocument();
		expect(getByLabelText('remax: nedostupný')).toBeInTheDocument();
	});

	test('shows a trigger error in place of the last-run label, taking priority over it', async () => {
		const { getByText, queryByText } = await renderWithTranslator(InboxHeader, {
			health: [],
			runState: { status: 'idle' },
			lastFinishedAt: new Date('2026-09-19T10:00:00Z'),
			triggerError: 'POST /v1/runs failed: 500 Internal Server Error',
			onrun: () => {}
		});
		expect(getByText(/POST \/v1\/runs failed/)).toBeInTheDocument();
		expect(queryByText(/^Poslední scan:/)).not.toBeInTheDocument();
	});

	test('shows a failed run even with no error message, not a stale success label', async () => {
		const { getByText, queryByText } = await renderWithTranslator(InboxHeader, {
			health: [],
			runState: { status: 'failed', profileId: 'a', error: null },
			lastFinishedAt: new Date('2026-09-19T10:00:00Z'),
			triggerError: null,
			onrun: () => {}
		});
		expect(getByText('Scan selhal')).toBeInTheDocument();
		expect(queryByText(/^Poslední scan:/)).not.toBeInTheDocument();
	});
});
