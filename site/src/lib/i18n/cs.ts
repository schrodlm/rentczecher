import type { Messages } from './messages';
import { CONTACT_EMAIL, ISSUES_URL, REPO_URL, SUPPORT_URL } from '$lib/links';

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
		defaults: 'Hned po instalaci hlídá rentczecher RE/MAX a iDNES Reality. Sreality a Bezrealitky si zapnete sami při nastavení profilu, až uvidíte, co jejich podmínky říkají o automatickém čtení.',
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
		installSteps: 'Jak ji nainstalovat, krok za krokem',
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
					title: 'Hlídání na pozadí',
					body: 'Kontroly poběží podle plánu i bez otevřeného okna. A když některá selže, dozvíte se to.'
				}
			]
		},
		next: {
			label: 'Brzy',
			items: [
				{
					title: 'Podepsaný instalátor pro Windows',
					body: 'Aby ho Windows otevřely bez varování.'
				},
				{
					title: 'Upozornění',
					body: 'Upozornění v počítači, když se objeví něco nového, a pokud chcete, i e-mail do vlastní schránky.'
				}
			]
		},
		later: {
			label: 'Později',
			items: [
				{
					title: 'Další realitní portály',
					body: 'Zatím čtyři. U každého dalšího nejdřív prověřím, co od aplikací žádá.'
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
					'RE/MAX, iDNES Reality, Bezrealitky a Sreality. RE/MAX a iDNES Reality jsou zapnuté od začátku. Sreality a Bezrealitky jsou ve výchozím stavu vypnuté a zapnete si je sami v profilu, až uvidíte, co daný portál žádá. Další portály přibudou, u každého nejdřív prověřím, co od aplikací žádá. rentczecher není s žádným z těchto portálů nijak spojený a žádný z nich ho nepodporuje.'
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
					'Aplikace zatím není podepsaná, takže oba systémy hlásí, že nevědí, kdo ji vytvořil. ',
					{ text: 'Postup instalace', href: '/install/' },
					' ukazuje, jak varování obejít ve Windows i na Macu. Stačí to udělat jednou.'
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
		privacyPolicy: 'Ochrana soukromí',
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
			'Čte stránky s výsledky hledání, mezi stránkami dělá pauzy a na jedno hledání přečte jen omezený počet stránek.',
			'Po kontrole stáhne u každé nové nabídky hlavní fotku. Samotný inzerát otevře a další fotky nabídky stáhne, jen když ji uživatel v aplikaci otevře nebo označí hvězdičkou, a to jen jednou.',
			'Nepoužívá proxy, nemění identitu a neobchází CAPTCHA ani firewall. Když ho portál odmítne, nesnaží se odmítnutí obejít.',
			'Portál, který ve svých podmínkách nebo v robots.txt automatické nástroje odmítá, je ve výchozím stavu vypnutý.'
		],
		contactHeading: 'Kontakt',
		contact: [
			'Pokud máte k tomu, jak rentczecher používá váš portál, jakoukoli připomínku, napište mi na ',
			{ text: CONTACT_EMAIL, href: `mailto:${CONTACT_EMAIL}` },
			'. Každá taková zpráva dostane rychlou odpověď.'
		],
		notAffiliated: 'rentczecher není s žádným realitním portálem nijak spojený a žádný ho nepodporuje.'
	},
	install: {
		title: 'Instalace ve Windows a na macOS',
		intro:
			'rentczecher zatím není podepsaný, takže vás Windows i macOS při prvním otevření varují. Tady je, jak varování obejít. Stačí to udělat jednou.',
		windowsHeading: 'Windows',
		windowsSteps: [
			{
				text: [
					'Stáhněte instalátor. Pokud ho Microsoft Edge zadrží, protože se často nestahuje, otevřete u stahování nabídku ',
					{ uiLabel: '⋯' },
					', zvolte ',
					{ uiLabel: 'Zachovat' },
					', potom ',
					{ uiLabel: 'Zobrazit další' },
					' a ',
					{ uiLabel: 'Přesto zachovat' },
					'.'
				],
				screenshot: null
			},
			{
				text: [
					'Otevřete instalátor. Windows ukáže modrou obrazovku ',
					{ uiLabel: 'Systém Windows ochránil váš počítač' },
					'. Klikněte na ',
					{ uiLabel: 'Další informace' },
					'.'
				],
				screenshot: null
			},
			{
				text: [
					'Zkontrolujte, že jde o aplikaci ',
					{ uiLabel: 'rentczecher-windows-x64-setup.exe' },
					', a klikněte na ',
					{ uiLabel: 'Přesto spustit' },
					'.'
				],
				screenshot: null
			},
			{
				text: ['Projděte instalací jako obvykle. Aplikace se pak otevírá bez varování, pokaždé.'],
				screenshot: null
			}
		],
		smartAppControlHeading: 'Chybí tlačítko Přesto spustit?',
		smartAppControl: [
			'Pak je zapnuté ',
			{ uiLabel: 'Inteligentní řízení aplikací' },
			', které blokuje každou nepodepsanou aplikaci a výjimku pro jednu aplikaci nedovolí. Vypnout ho můžete v ',
			{ uiLabel: 'Zabezpečení Windows' },
			' → ',
			{ uiLabel: 'Řízení aplikací a prohlížeče' },
			' → ',
			{ uiLabel: 'Nastavení Inteligentního řízení aplikací' },
			'. Ve starších Windows 11 bez aktualizací z roku 2026 už ho pak nejde zapnout jinak než přeinstalováním Windows, takže to udělejte, jen pokud si jste jistí.'
		],
		macosHeading: 'macOS',
		macosSteps: [
			{
				text: [
					'Stáhněte instalátor, otevřete ho a přetáhněte ',
					{ uiLabel: 'rentczecher' },
					' do složky ',
					{ uiLabel: 'Aplikace' },
					'.'
				],
				screenshot: null
			},
			{
				text: [
					'Otevřete rentczecher ze složky Aplikace. macOS oznámí, že nemohl ověřit, zda aplikace neobsahuje malware. Klikněte na ',
					{ uiLabel: 'Hotovo' },
					'.'
				],
				screenshot: null
			},
			{
				text: [
					'Otevřete ',
					{ uiLabel: 'Nastavení systému' },
					' → ',
					{ uiLabel: 'Soukromí a zabezpečení' },
					' a sjeďte dolů k části Zabezpečení. U hlášky, že rentczecher byl zablokován, klikněte na ',
					{ uiLabel: 'Přesto otevřít' },
					'. Tlačítko tam zůstává asi hodinu od chvíle, kdy jste aplikaci zkusili otevřít.'
				],
				screenshot: null
			},
			{
				text: [
					'Zadejte heslo nebo použijte Touch ID a ještě jednou klikněte na ',
					{ uiLabel: 'Přesto otevřít' },
					'. Od té chvíle se aplikace otevírá normálně.'
				],
				screenshot: null
			}
		],
		olderMacos: [
			'Na macOS 14 Sonoma a starších je to rychlejší. Klikněte na aplikaci ve složce Aplikace se stisknutou klávesou Control, zvolte ',
			{ uiLabel: 'Otevřít' },
			' a pak ještě jednou ',
			{ uiLabel: 'Otevřít' },
			'.'
		],
		damagedHeading: 'macOS tvrdí, že je aplikace poškozená?',
		damaged: [
			'Aplikace je v pořádku. macOS to o aplikacích mimo App Store občas tvrdí a pak tlačítko ',
			{ uiLabel: 'Přesto otevřít' },
			' nenabídne. Otevřete ',
			{ uiLabel: 'Terminál' },
			', vložte tento řádek a stiskněte Enter. Odstraní značku, kterou macOS stažené aplikaci dal, a aplikace se pak otevře.'
		],
		damagedCommand: 'xattr -dr com.apple.quarantine /Applications/rentczecher.app',
		whyHeading: 'Proč to varování?',
		why: [
			'Windows i macOS aplikaci věří, když je podepsaná certifikátem, který jmenuje jejího vývojáře. rentczecher zatím podepsaný není, takže oba systémy hlásí, že nevědí, kdo ho vytvořil. O tom, jestli je aplikace bezpečná, neříkají nic.',
			'Podepsaný instalátor pro Windows chystám. Na macOS podepisování vyžaduje developerský program od Applu za €99 ročně a já na aplikaci nic nevydělávám. Na Macu tedy varování zatím zůstane.',
			'Každý řádek aplikace je veřejně na GitHubu a každý instalátor se tam z tohoto kódu sestavuje.'
		]
	},
	privacyPolicy: {
		title: 'Ochrana soukromí',
		intro: 'rentczecher nesbírá žádné osobní údaje. Tato stránka uvádí všechna spojení, která aplikace a tento web navazují, takže přesně vidíte, kam vaše data putují.',
		keepsHeading: 'Co si aplikace ukládá',
		keeps: [
			'Vaše profily, uložené a skryté nabídky, fotky a historie cen zůstávají jen na vašem počítači, ve vlastní datové složce aplikace.',
			'Nemá žádný účet, server, analytiku, hlášení pádů ani sledování. Autorovi se nikdy nic neposílá.',
			'Odinstalováním aplikace a smazáním její datové složky zmizí vše, co si uložila.',
			'Vybrané profily můžete uložit do souboru a přidat je na jiném počítači. Soubor obsahuje vaše hledání a jejich preference, nikdy nabídky, a zůstává tam, kam ho uložíte, i po odinstalování aplikace.'
		],
		connectionsHeading: 'S kým aplikace komunikuje',
		connectionsIntro: 'Aplikace se připojuje jen ke službám níže, ke každé jen za uvedeným účelem. Každá z nich vidí vaši IP adresu, stejně jako každý web, který navštívíte.',
		connections: [
			'Realitní portály, které zapnete, a jejich servery s obrázky. Když spustíte kontrolu, přečte vaše uložená hledání a u každé nové nabídky stáhne hlavní fotku. Inzerát a další fotky nabídky čte, když ji otevřete nebo označíte hvězdičkou.',
			'Server s dlaždicemi OpenStreetMap (tile.openstreetmap.org), aby mohla vykreslit mapy ulic.',
			'Veřejné servery Overpass projektu OpenStreetMap (overpass-api.de, overpass.private.coffee, overpass.kumi.systems), aby našla místa v okolí, třeba obchody nebo zastávky. Dostanou jen výřez mapy kolem nabídky a druhy hledaných míst, nic dalšího.',
			'GitHub (github.com, stahování obsluhuje githubusercontent.com), kde vycházejí nové verze aplikace. Aplikace se při spuštění a pak jednou denně zeptá, zda je k dispozici novější verze, a stáhne ji, jen když se rozhodnete aktualizovat. GitHub každý dotaz i stažení započítá, takže autor vidí, jak často se aplikace ptá, ale ne, kdo se ptal.',
			'Odkaz na inzerát, Mapy.com nebo Google Mapy se otevře ve vašem prohlížeči a odtamtud platí zásady ochrany soukromí daného webu.'
		],
		siteHeading: 'Tento web',
		site: [
			'rentczecher.cz je statický web hostovaný na GitHub Pages. Neukládá žádné cookies a nepoužívá žádnou analytiku.',
			'GitHub jako hostitel může zaznamenávat technické údaje, například vaši IP adresu, podle svých vlastních zásad ochrany soukromí.',
			'Zvolený světlý nebo tmavý motiv si pamatuje jen váš prohlížeč.'
		],
		contactHeading: 'Kontakt',
		contact: [
			'Dotazy k ochraně soukromí posílejte na ',
			{ text: CONTACT_EMAIL, href: `mailto:${CONTACT_EMAIL}` },
			'.'
		],
		updated: 'Naposledy aktualizováno 31. října 2026.'
	}
};
