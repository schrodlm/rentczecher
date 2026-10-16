import type { Messages } from './messages';
import { ISSUES_URL, OPERATOR_CONTACT_EMAIL, REPO_URL, SUPPORT_URL } from '$lib/links';

export const cs: Messages = {
	meta: {
		title: 'rentczecher',
		description:
			'rentczecher za vás hlídá hlavní české realitní portály a ukáže jen to, co je opravdu nové. Včetně zlevnění. Zdarma a open source.'
	},
	topbar: 'rentczecher je open source. Celý kód najdete na GitHubu, hvězdička potěší →',
	nav: {
		label: 'Hlavní',
		features: 'Co umí',
		how: 'Jak to funguje',
		roadmap: 'Co chystám',
		devlog: 'Devlog',
		faq: 'Otázky'
	},
	languageLabel: 'Jazyk',
	theme: {
		toDark: 'Přepnout na tmavý režim',
		toLight: 'Přepnout na světlý režim'
	},
	hero: {
		badge: 'Open source na GitHubu, licence GPL-3.0',
		lead: 'Každý den přibývají nové ',
		kinds: ['byty', 'domy', 'chaty'],
		kindsLabel: 'byty, domy a chaty',
		tail: '',
		promise: 'Pomůžu vám je najít.',
		intro:
			'rentczecher za vás hlídá hlavní české realitní portály a ukáže jen to, co je opravdu nové. Včetně zlevnění.',
		download: 'Stáhnout',
		source: 'Zdrojový kód na GitHubu',
		freeVersion: (version) => `Zdarma, verze ${version}.`,
		platforms: 'Pro Windows, macOS a Linux.',
		mapLabel: 'Mapa Česka, na které přibývají nové byty, domy a chaty',
		newBadge: 'NOVÝ',
		newAgo: 'před 3 min',
		newTitle: 'Byt 2+kk, 54 m²',
		newDetail: 'Brno, Žabovřesky, 18 900 Kč/měs.',
		dropBadge: 'ZLEVNĚNO',
		dropAgo: 'dnes',
		dropTitle: 'Chata, 3 pokoje',
		dropDetail: 'Šumava, 2 450 000 Kč',
		dropAmount: '−150 000'
	},
	portals: {
		label: 'Podporované portály',
		heading: 'Portály',
		defaults: 'Hned po instalaci hlídá rentczecher RE/MAX. Sreality a Bezrealitky si zapnete sami při nastavení profilu, až uvidíte, co jejich podmínky říkají o automatickém čtení.',
		more: '+ další brzy',
		notAffiliated: 'rentczecher není s žádným z těchto portálů nijak spojený a žádný z nich ho nepodporuje.'
	},
	features: {
		heading: 'Zápisník pro vaše hledání bydlení',
		intro: 'Nabídky najdete na portálech a tam se také domluvíte s prodávajícím. rentczecher si k tomu vede poznámky: co je nové, co jste už viděli a jak se měnily ceny. Inzerát si vždycky přečtete na portálu, odkud pochází.',
		cards: {
			onlyNew: {
				title: 'Jen nové',
				body: 'Ukáže vám, co jste ještě neviděli, a zlevnění toho, co už znáte.'
			},
			oneList: {
				title: 'Jeden seznam',
				body: 'Stejný byt z více portálů se ukáže jednou, s odkazem na každý jeho inzerát.'
			},
			memory: {
				title: 'Paměť',
				body: 'Pamatuje si, co jste viděli, co se vám líbí a jak se měnila cena.'
			},
			backToPortal: {
				title: 'Zpátky na portál',
				body: 'Každá nabídka vede na svůj inzerát. Tam si ho přečtete a ozvete se prodávajícímu.'
			},
			privacy: {
				title: 'Soukromí',
				body: 'Běží jen u vás v počítači. Bez účtu a bez cloudu.'
			},
			free: {
				title: 'Zdarma',
				body: 'Bez předplatného a bez placené verze.'
			}
		}
	},
	how: {
		heading: 'Jak to funguje',
		stepsLabel: 'Kroky',
		previous: 'Předchozí krok',
		next: 'Další krok',
		steps: {
			search: {
				title: 'Řekněte, co hledáte',
				body: 'Pronájem nebo koupě. Byt, dům, chata nebo pozemek. Místo na mapě, cena, velikost a dispozice. Klidně několik profilů najednou.',
				screenshotAlt: 'Nový profil v aplikaci: typ nabídky, mapa Česka pro výběr místa, rozpětí ceny a velikosti a dispozice'
			},
			preferences: {
				title: 'Vyberte, co preferujete',
				body: 'Cena, velikost nebo dispozice, podle toho, na čem vám záleží nejvíc. Hned vidíte, jak by nabídky bodovaly. A vyberete portály, které má hlídat.',
				screenshotAlt: 'Preference v aplikaci: zapnuté portály, váha ceny, velikosti a dispozice a ukázka, jak by inzeráty bodovaly'
			},
			inbox: {
				title: 'Projdete jen novinky',
				body: 'Stisknete Spustit scan a projde zapnuté portály, pak ukáže nové nabídky a zlevnění, seřazené podle toho, jak dobře vám sedí.',
				screenshotAlt: 'Schránka v aplikaci: nové nabídky seřazené podle skóre a rozpis skóre vybrané nabídky'
			}
		}
	},
	privacy: {
		heading: 'Všechno zůstává u vás.',
		body: 'rentczecher nemá žádný server. Vaše profily, oblíbené nabídky i historie cen jsou uložené jen ve vašem počítači. Žádný účet, žádné sledování. A protože je kód otevřený, můžete si to sami ověřit.'
	},
	openSource: {
		chip: 'Open source',
		heading: 'Vzniká veřejně na GitHubu.',
		body: 'Celý kód je veřejný. Můžete si ho přečíst, nahlásit chybu, navrhnout funkci nebo rovnou přispět. Každá hvězdička pomáhá, aby se o projektu dozvědělo víc lidí.',
		star: 'Dát hvězdičku na GitHubu',
		reportBug: 'Nahlásit chybu',
		repoDescription: 'Hlídač nových nabídek z českých realitních portálů. Běží lokálně.',
		licence: 'Licence',
		authorHeading: 'Dělá to jeden člověk, po večerech.',
		authorBody:
			'rentczecher vyvíjím sám, ve svém volném čase, a nic za to nečekám. Pokud vám ale ušetřil hodiny scrollování a chcete poděkovat, budu rád za kávu.',
		support: 'Poděkovat'
	},
	download: {
		heading: 'Stáhnout',
		version: 'Verze',
		free: 'zdarma',
		allReleases: 'Všechny verze a poznámky k vydání na GitHubu',
		button: 'Stáhnout',
		windows: 'Instalátor .exe pro Windows 10 a 11',
		macos: 'Instalátor .dmg pro Apple Silicon',
		linux: 'AppImage nebo .deb',
		firstLaunchWarning: 'Aplikace zatím není podepsaná, takže Windows i macOS při prvním spuštění varují.',
		whatToDo: 'Co s tím?',
		buildYourself: 'Raději si to sestavíte sami?',
		readme: 'Návod je v README'
	},
	roadmap: {
		heading: 'Co chystám',
		intro: 'Plán se mění podle toho, co lidé potřebují. Chybí vám něco? Napište to na GitHub.',
		suggest: 'Navrhnout funkci',
		inProgress: {
			label: 'Právě dělám',
			items: [
				{
					title: 'Profily přímo v aplikaci',
					body: 'Profily vytvoříte, upravíte i smažete v aplikaci. A oblíbené nabídky si odložíte stranou.'
				}
			]
		},
		next: {
			label: 'Brzy',
			items: [
				{
					title: 'Hlídání na pozadí',
					body: 'Kontroly poběží podle plánu i bez otevřeného okna. A když některá selže, dozvíte se to.'
				},
				{
					title: 'Fotky u oblíbených bytů',
					body: 'Fotky nabídek uvidíte přímo v aplikaci a u bytů s hvězdičkou zůstanou uložené.'
				}
			]
		},
		later: {
			label: 'Později',
			items: [
				{
					title: 'Snadný první start',
					body: 'E-mail i první profil nastavíte v aplikaci, bez úprav konfiguračních souborů.'
				},
				{
					title: 'Další realitní portály',
					body: 'U každého nejdřív prověřím, co od aplikací žádá.'
				},
				{
					title: 'Na jiném počítači',
					body: 'Hlídání poběží na jednom počítači a připojíte se k němu z ostatních zařízení.'
				}
			]
		}
	},
	devlog: {
		heading: 'Devlog',
		intro: 'Jak rentczecher vzniká: co se povedlo, co ne a co jsem se cestou naučil.',
		writtenInEnglish: 'Příspěvky píšu anglicky.',
		allPosts: 'Všechny příspěvky',
		read: 'Číst',
		minutesToRead: (minutes) => `${minutes} min čtení`
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
					'RE/MAX, Bezrealitky a Sreality. RE/MAX je zapnutý od začátku. Sreality a Bezrealitky jsou ve výchozím stavu vypnuté a zapnete si je sami v profilu, až uvidíte, co daný portál žádá. Další portály přibudou, u každého nejdřív prověřím, co od aplikací žádá. rentczecher není s žádným z těchto portálů nijak spojený a žádný z nich ho nepodporuje.'
				]
			},
			{
				question: 'Hlídá, i když mám počítač vypnutý?',
				answer: [
					'Ne. Portály projde, když stisknete Spustit scan, se zapnutým počítačem a otevřenou aplikací. Kontroly na pozadí chystám. Co se mezitím objevilo, uvidíte při dalším scanu.'
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
				question: 'Proč mě Windows a macOS varují?',
				answer: [
					'Aplikace zatím není podepsaná. Ve Windows zvolte ',
					{ uiLabel: 'Další informace' },
					' a pak ',
					{ uiLabel: 'Přesto spustit' },
					'. Podepsaný instalátor pro Windows chystám. ',
					'Na macOS je pro podepsání nutné zakoupit developerský program v ceně €99/rok. Za aplikaci nic nevydělávám, takže nemám důvod za to platit. Aplikaci je pořád možné spustit, i když je s tím trošku více práce. Otevřete ',
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
	},
	footer: {
		label: 'Odkazy',
		credit:
			'Vytvořil Matěj Schrödl. Nezávislý open-source projekt, nijak nespojený s žádným realitním portálem.',
		operators: 'Pro provozovatele portálů',
		support: 'Poděkovat'
	},
	operators: {
		title: 'Pro provozovatele portálů',
		intro: 'Pokud jste sem přišli z hlavičky User-Agent ve svých logech, tady je, co je rentczecher a jak čte váš web.',
		whatHeading: 'Co to je',
		whatItIs: [
			'Bezplatná desktopová aplikace s otevřeným kódem pod licencí GPL-3.0-or-later.',
			'Spouští ji jeden člověk na vlastním počítači pro vlastní hledání bydlení.',
			'Nemá žádný server ani účty a uživatelé mezi sebou nesdílejí žádná data.',
			'Nabídky nikdy dál nezveřejňuje, neukládá texty inzerátů a každou nabídku odkazuje zpět na její inzerát.'
		],
		howHeading: 'Jak čte váš web',
		userAgentIntro: 'V každém požadavku se představí touto hlavičkou User-Agent:',
		howItReads: [
			'Čte jen uložená hledání svého uživatele, a to když uživatel spustí kontrolu.',
			'Čte stránky s výsledky hledání, mezi stránkami dělá pauzy a samotné inzeráty nikdy neotevírá.',
			'Nepoužívá proxy, nemění identitu a neobchází CAPTCHA ani firewall. Když ho portál odmítne, nesnaží se odmítnutí obejít.',
			'Portál, který ve svých podmínkách nebo v robots.txt automatické nástroje odmítá, je ve výchozím stavu vypnutý.'
		],
		contactHeading: 'Kontakt',
		contact: [
			'Pokud máte k tomu, jak rentczecher používá váš portál, jakoukoli připomínku, napište mi na ',
			{ text: OPERATOR_CONTACT_EMAIL, href: `mailto:${OPERATOR_CONTACT_EMAIL}` },
			'. Každá taková zpráva dostane rychlou odpověď.'
		],
		notAffiliated: 'rentczecher není s žádným realitním portálem nijak spojený a žádný ho nepodporuje.'
	}
};
