import { fireEvent, screen } from '@testing-library/svelte';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { renderWithTranslator } from '$lib/test-support/render';

const shell = vi.hoisted(() => ({
	calls: [] as string[],
	failing: null as string | null
}));

vi.mock('@tauri-apps/api/core', () => ({
	invoke: async (command: string) => {
		shell.calls.push(command);
		if (command === shell.failing) throw new Error('no mail client');
		if (command === 'app_details') return { version: '0.2.0', os: 'linux', arch: 'x86_64' };
	}
}));

const { default: FeedbackDialog } = await import('./FeedbackDialog.svelte');

afterEach(() => {
	shell.calls = [];
	shell.failing = null;
});

async function openDialog(): Promise<{ onclose: ReturnType<typeof vi.fn> }> {
	const onclose = vi.fn();
	await renderWithTranslator(FeedbackDialog, { onclose });
	await screen.findByText('Přiloží se: rentczecher 0.2.0 · Linux x86_64');
	return { onclose };
}

describe('FeedbackDialog', () => {
	test('keeps both ways of sending off until there is a message', async () => {
		await openDialog();
		const email = screen.getByRole('button', { name: 'Poslat e-mailem' }) as HTMLButtonElement;
		const issue = screen.getByRole('button', { name: 'Založit issue na GitHubu' }) as HTMLButtonElement;
		expect(email.disabled).toBe(true);
		expect(issue.disabled).toBe(true);

		await fireEvent.input(screen.getByRole('textbox'), { target: { value: '   ' } });
		expect(email.disabled).toBe(true);

		await fireEvent.input(screen.getByRole('textbox'), { target: { value: 'Mapa nefunguje' } });
		expect(email.disabled).toBe(false);
		expect(issue.disabled).toBe(false);
	});

	test('stays open with the message once the email draft is open', async () => {
		const { onclose } = await openDialog();
		await fireEvent.input(screen.getByRole('textbox'), { target: { value: 'Mapa nefunguje' } });
		await fireEvent.click(screen.getByRole('button', { name: 'Poslat e-mailem' }));
		await screen.findByText('E-mail se otevřel ve vašem poštovním programu.');
		expect(shell.calls).toContain('open_mail_draft');
		expect(onclose).not.toHaveBeenCalled();
		expect((screen.getByRole('textbox') as HTMLTextAreaElement).value).toBe('Mapa nefunguje');
	});

	test('stays open with the reason when the draft cannot be opened', async () => {
		shell.failing = 'open_mail_draft';
		const { onclose } = await openDialog();
		await fireEvent.input(screen.getByRole('textbox'), { target: { value: 'Mapa nefunguje' } });
		await fireEvent.click(screen.getByRole('button', { name: 'Poslat e-mailem' }));
		await screen.findByText('Koncept se nepodařilo otevřít: no mail client');
		expect(onclose).not.toHaveBeenCalled();
	});

	test('opens the log folder', async () => {
		await openDialog();
		await fireEvent.click(screen.getByRole('button', { name: 'Zobrazit soubor s logem' }));
		await vi.waitFor(() => expect(shell.calls).toContain('open_log_folder'));
	});

	test('closes on a click beside it only while no message is written', async () => {
		const { onclose } = await openDialog();
		const backdrop = document.querySelector('.feedback__backdrop') as HTMLElement;
		await fireEvent.input(screen.getByRole('textbox'), { target: { value: 'Mapa nefunguje' } });
		await fireEvent.click(backdrop);
		expect(onclose).not.toHaveBeenCalled();

		await fireEvent.input(screen.getByRole('textbox'), { target: { value: '' } });
		await fireEvent.click(backdrop);
		expect(onclose).toHaveBeenCalledOnce();
	});
});
