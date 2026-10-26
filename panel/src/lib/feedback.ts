import { invoke } from '@tauri-apps/api/core';

/* What the app is and what it runs on. The shell's app_details command
replies in exactly this shape. */
export type AppDetails = { version: string; os: string; arch: string };

const FEEDBACK_EMAIL = 'matej.schrodl@gmail.com';
const NEW_ISSUE_URL = 'https://github.com/schrodlm/rentczecher/issues/new';

// Keeps the GitHub issue's URL under the length GitHub accepts, even when
// every character is Czech and encodes to six.
export const MESSAGE_MAX_LENGTH = 1000;

// The shell names the OS the way Rust does.
const OS_NAMES: Record<string, string> = { linux: 'Linux', macos: 'macOS', windows: 'Windows' };

export async function appDetails(): Promise<AppDetails> {
	return invoke<AppDetails>('app_details');
}

export async function openLogFolder(): Promise<void> {
	return invoke<void>('open_log_folder');
}

/* A message a user writes to the author, with the details of their app
below it, ready to send by email or as a GitHub issue. Nothing leaves the
app on its own: each way only opens a draft the user sends themselves. */
export class Feedback {
	constructor(
		private readonly message: string,
		private readonly details: AppDetails
	) {}

	get detailsLine(): string {
		const os = OS_NAMES[this.details.os] ?? this.details.os;
		return `rentczecher ${this.details.version} · ${os} ${this.details.arch}`;
	}

	emailUrl(subject: string): string {
		// Mail wants its line breaks as CRLF.
		const body = this.body.replaceAll('\n', '\r\n');
		return `mailto:${FEEDBACK_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
	}

	issueUrl(): string {
		return `${NEW_ISSUE_URL}?body=${encodeURIComponent(this.body)}`;
	}

	async sendByEmail(subject: string): Promise<void> {
		await invoke('open_mail_draft', { url: this.emailUrl(subject) });
	}

	async sendAsIssue(): Promise<void> {
		await invoke('open_in_browser', { url: this.issueUrl() });
	}

	private get body(): string {
		return `${this.message.trim()}\n\n---\n${this.detailsLine}`;
	}
}
