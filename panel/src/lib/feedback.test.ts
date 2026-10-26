import { afterEach, describe, expect, test, vi } from 'vitest';

const shell = vi.hoisted(() => ({ calls: [] as { command: string; args: unknown }[] }));

vi.mock('@tauri-apps/api/core', () => ({
	invoke: async (command: string, args: unknown) => {
		shell.calls.push({ command, args });
	}
}));

const { Feedback } = await import('./feedback');

const LINUX = { version: '0.2.0', os: 'linux', arch: 'x86_64' };

afterEach(() => {
	shell.calls = [];
});

describe('Feedback', () => {
	test('names the version, the OS as people write it, and the architecture', () => {
		expect(new Feedback('hi', LINUX).detailsLine).toBe('rentczecher 0.2.0 · Linux x86_64');
		expect(new Feedback('hi', { ...LINUX, os: 'macos', arch: 'aarch64' }).detailsLine).toBe(
			'rentczecher 0.2.0 · macOS aarch64'
		);
	});

	test('shows an OS it has no name for as the shell reports it', () => {
		expect(new Feedback('hi', { ...LINUX, os: 'freebsd' }).detailsLine).toBe('rentczecher 0.2.0 · freebsd x86_64');
	});

	test('drafts an email to the author with the message above the details, in CRLF lines', () => {
		const url = new URL(new Feedback('  Mapa nefunguje & padá  \n', LINUX).emailUrl('Zpětná vazba'));
		expect(url.protocol).toBe('mailto:');
		expect(url.pathname).toBe('matej.schrodl@gmail.com');
		expect(url.searchParams.get('subject')).toBe('Zpětná vazba');
		expect(url.searchParams.get('body')).toBe('Mapa nefunguje & padá\r\n\r\n---\r\nrentczecher 0.2.0 · Linux x86_64');
	});

	test('drafts a new GitHub issue on the repo with the message above the details', () => {
		const url = new URL(new Feedback('Idea', LINUX).issueUrl());
		expect(url.origin + url.pathname).toBe('https://github.com/schrodlm/rentczecher/issues/new');
		expect(url.searchParams.get('body')).toBe('Idea\n\n---\nrentczecher 0.2.0 · Linux x86_64');
	});

	test('opens the email draft through the shell, never the browser', async () => {
		const feedback = new Feedback('Idea', LINUX);
		await feedback.sendByEmail('Subject');
		expect(shell.calls).toEqual([{ command: 'open_mail_draft', args: { url: feedback.emailUrl('Subject') } }]);
	});

	test('opens the issue draft in the browser', async () => {
		const feedback = new Feedback('Idea', LINUX);
		await feedback.sendAsIssue();
		expect(shell.calls).toEqual([{ command: 'open_in_browser', args: { url: feedback.issueUrl() } }]);
	});
});
