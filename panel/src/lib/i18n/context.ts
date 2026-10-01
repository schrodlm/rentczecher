import { getContext, setContext } from 'svelte';
import { Translator } from './translator';

const CONTEXT_KEY = Symbol('translator');

export function setTranslatorContext(translator: Translator): void {
	setContext(CONTEXT_KEY, translator);
}

export function getTranslatorContext(): Translator {
	const translator = getContext<Translator>(CONTEXT_KEY);
	if (!translator) {
		throw new Error('no Translator in context, call setTranslatorContext in a parent first');
	}
	return translator;
}
