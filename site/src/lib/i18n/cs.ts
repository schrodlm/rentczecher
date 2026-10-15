import type { Messages } from './messages';
import { ISSUES_URL, REPO_URL, SUPPORT_URL } from '$lib/links';

export const cs: Messages = {
	meta: {
		title: 'rentczecher',
		description:
			'rentczecher za vás hlídá hlavní české realitní portály a ukáže jen to, co je opravdu nové. Včetně zlevnění. Zdarma a open source.'
	},
	topbar: 'rentczecher je open source. Celý kód najdete na GitHubu, hvězdička potěší →',
	nav: {
		label: 'Hlavní',
		faq: 'Otázky'
	},
	languageLabel: 'Jazyk',
	theme: {
		toDark: 'Přepnout na tmavý režim',
		toLight: 'Přepnout na světlý režim'
	},
	faq: {
		heading: 'Otázky',
		items: [
			{
				question: 'Je to opravdu zdarma?',
				answer: ['Ano. Žádné předplatné, žádné reklamy, žádný placený tarif.']
			},
			{
				question: 'Které portály hlídá?',
				answer: [
					'RE/MAX, Bezrealitky a Sreality. RE/MAX je zapnutý od začátku. Sreality a Bezrealitky jsou ve výchozím stavu vypnuté a zapnete si je sami v profilu, až uvidíte, co daný portál žádá. Další portály přibudou, jako první plánuji iDNES. rentczecher není s žádným z těchto portálů nijak spojený a žádný z nich ho nepodporuje.'
				]
			},
			{
				question: 'Hlídá, i když mám počítač vypnutý?',
				answer: [
					'Ne, hlídá, dokud aplikace běží, podle nastavené periody. Po zapnutí dožene, co se mezitím objevilo.'
				]
			},
			{
				question: 'Je kód opravdu otevřený?',
				answer: [
					'Ano, celý je na ',
					{ text: 'GitHubu', href: REPO_URL },
					' pod licencí GPL-3.0. Chyby a nápady můžete hlásit přes ',
					{ text: 'Issues', href: ISSUES_URL },
					'.'
				]
			},
			{
				question: 'Proč mě macOS varuje?',
				answer: [
					'Pro podporované vydání aplikace na macOS je nutné zakoupit developerský program v ceně €99/rok. Za aplikaci nic nevydělávám, takže nemám důvod za to platit. Aplikaci je pořád možné spustit, i když je s tím trošku více práce. Otevřete ',
					{ uiLabel: 'Nastavení systému' },
					' → ',
					{ uiLabel: 'Soukromí a zabezpečení' },
					' a u rentczecher zvolte ',
					{ uiLabel: 'Přesto otevřít' },
					'.'
				]
			},
			{
				question: 'Kdo za tím stojí?',
				answer: [
					'Jmenuji se Matěj a studuji na Matfyzu počítačovou vědu. Tento projekt vyvíjím ve volném čase a zdarma. Pokud chcete, můžete projekt ',
					{ text: 'podpořit', href: SUPPORT_URL },
					'. Jsem moc rád za jakoukoliv podporu, pomáhá udržovat projekt naživu.'
				]
			}
		]
	}
};
