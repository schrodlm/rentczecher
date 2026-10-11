import { invoke, isTauri } from '@tauri-apps/api/core';

/* Makes a link to another site open in the default browser. The app's window
opens no new windows of its own, so a link that asks for one does nothing
there. Outside the app, as in a browser tab, the link works as it is. */
export function opensInBrowser(link: HTMLAnchorElement): { destroy: () => void } {
	function onclick(event: MouseEvent): void {
		if (!isTauri()) return;
		event.preventDefault();
		void invoke('open_in_browser', { url: link.href });
	}

	link.addEventListener('click', onclick);
	return { destroy: () => link.removeEventListener('click', onclick) };
}
