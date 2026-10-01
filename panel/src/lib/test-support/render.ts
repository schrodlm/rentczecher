import { render } from '@testing-library/svelte';
import type { Component, ComponentProps } from 'svelte';
import { Translator } from '$lib/i18n/translator';
import TranslatorProvider from './TranslatorProvider.svelte';

/* Every component under test reads the translator from context via
getTranslatorContext(), so tests render through the same wrapper the app's
root layout uses instead of duplicating context setup per test. */
export async function renderWithTranslator<P extends Record<string, unknown>>(
	SvelteComponent: Component<P>,
	props: ComponentProps<Component<P>>
) {
	const translator = await Translator.load('cs');
	return render(SvelteComponent, props, {
		wrapper: TranslatorProvider,
		wrapperProps: { translator }
	});
}
