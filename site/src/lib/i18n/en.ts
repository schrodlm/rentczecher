import type { Messages } from './messages';
import { CONTACT_EMAIL, ISSUES_URL, REPO_URL, SUPPORT_URL } from '$lib/links';

export const en: Messages = {
	meta: {
		title: 'rentczecher',
		description:
			"rentczecher keeps an eye on the major Czech real-estate portals and shows you only what's actually new. Price drops included. Free and open source."
	},
	topbar: 'rentczecher is open source. All the code is on GitHub, a star is always appreciated →',
	nav: {
		label: 'Main',
		features: 'Features',
		how: 'How it works',
		roadmap: 'Roadmap',
		devlog: 'Devlog',
		faq: 'FAQ'
	},
	languageLabel: 'Language',
	theme: {
		toDark: 'Switch to dark mode',
		toLight: 'Switch to light mode'
	},
	hero: {
		badge: 'Open source on GitHub, GPL-3.0 licence',
		lead: 'New ',
		kinds: ['flats', 'houses', 'cottages'],
		kindsLabel: 'flats, houses and cottages',
		tail: ' every day.',
		promise: "I'll help you find them.",
		intro:
			"rentczecher keeps an eye on the major Czech real-estate portals and shows you only what's actually new. Price drops included.",
		download: 'Download',
		source: 'Source on GitHub',
		freeVersion: (version) => `Free, version ${version}.`,
		platforms: 'For Windows, macOS and Linux.',
		mapLabel: 'Map of Czechia with new flats, houses and cottages appearing',
		newBadge: 'NEW',
		newAgo: '3 min ago',
		newTitle: '2+kk flat, 54 m²',
		newDetail: 'Brno, Žabovřesky, 18,900 CZK/month',
		dropBadge: 'PRICE DROP',
		dropAgo: 'today',
		dropTitle: 'Cottage, 3 rooms',
		dropDetail: 'Šumava, 2,450,000 CZK',
		dropAmount: '−150,000'
	},
	portals: {
		label: 'Supported portals',
		heading: 'Portals',
		defaults: 'RE/MAX is watched right after you install. Sreality and Bezrealitky you turn on yourself when you set up a profile, after seeing what their terms say about automated reading.',
		more: '+ more soon',
		notAffiliated: 'rentczecher is not affiliated with, endorsed by or connected to any of these portals.'
	},
	features: {
		heading: 'A notebook for your home search',
		intro: 'The portals are where listings live and where you talk to the seller. rentczecher keeps notes alongside: what is new, what you have already seen and how prices moved. To read an advert, it always sends you back to the portal it came from.',
		cards: {
			onlyNew: {
				title: "Only what's new",
				body: "It shows you what you haven't seen yet, and price drops on what you already know."
			},
			oneList: {
				title: 'One list',
				body: 'The same flat from several portals shows up once, with a link to each of its postings.'
			},
			memory: {
				title: 'Memory',
				body: "It remembers what you've seen, what you liked and how the price changed."
			},
			backToPortal: {
				title: 'Back to the portal',
				body: 'Every listing links to its advert. You read it there and contact the seller there.'
			},
			privacy: {
				title: 'Privacy',
				body: 'It runs only on your computer. No account, no cloud.'
			},
			free: {
				title: 'Free',
				body: 'No subscription and no paid version.'
			}
		}
	},
	how: {
		heading: 'How it works',
		stepsLabel: 'Steps',
		previous: 'Previous step',
		next: 'Next step',
		steps: {
			search: {
				title: "Tell it what you're after",
				body: 'Rent or buy. A flat, house, cottage or plot. A spot on the map, price, size and layout. Several profiles at once, if you like.',
				screenshotAlt: 'A new profile in the app: the kind of offer, a map of Czechia to pick the place, price and size ranges and layouts'
			},
			preferences: {
				title: 'Pick what you prefer',
				body: 'Price, size or layout, whichever matters most to you. You see right away how listings would score. And you choose which portals it watches.',
				screenshotAlt: 'Preferences in the app: the portals turned on, the weight of price, size and layout and a preview of how listings would score'
			},
			inbox: {
				title: "Go through only what's new",
				body: 'Press Run scan and it checks the portals you turned on, then shows new listings and price drops, sorted by how well they fit you.',
				screenshotAlt: "The app's inbox: new listings sorted by score, with the selected listing's score breakdown"
			}
		}
	},
	privacy: {
		heading: 'Everything stays with you.',
		body: 'rentczecher has no server. Your profiles, saved listings and price history live only on your computer. No account, no tracking. And because the code is open, you can check that yourself.'
	},
	openSource: {
		chip: 'Open source',
		heading: 'Built in the open on GitHub.',
		body: 'All of the code is public. Read it, report a bug, suggest a feature or contribute directly. Every star helps more people find the project.',
		star: 'Star on GitHub',
		reportBug: 'Report a bug',
		repoDescription: 'Watches Czech real-estate portals for new listings. Runs locally.',
		licence: 'Licence',
		authorHeading: 'Made by one person, in the evenings.',
		authorBody:
			"I build rentczecher on my own, in my free time, and don't expect anything for it. But if it saved you hours of scrolling and you'd like to say thanks, a coffee is always welcome.",
		support: 'Say thanks'
	},
	download: {
		heading: 'Download',
		version: 'Version',
		free: 'free',
		allReleases: 'All versions and release notes on GitHub',
		button: 'Download',
		windows: '.exe installer for Windows 10 and 11',
		macos: '.dmg installer for Apple Silicon',
		linux: 'AppImage or .deb',
		firstLaunchWarning: 'The app is not code-signed yet, so Windows and macOS warn you on first launch.',
		whatToDo: 'What to do?',
		buildYourself: 'Prefer to build it yourself?',
		readme: 'See the README'
	},
	roadmap: {
		heading: "What's coming",
		intro: 'The plan follows what people need. Missing something? Say so on GitHub.',
		suggest: 'Suggest a feature',
		inProgress: {
			label: 'In progress',
			items: [
				{
					title: 'The first release',
					body: 'Installers for Windows, macOS and Linux, then a signed Windows installer so it opens without a warning.'
				}
			]
		},
		next: {
			label: 'Next',
			items: [
				{
					title: 'Watching in the background',
					body: 'Checks run on a schedule with no window open. And if one fails, you hear about it.'
				},
				{
					title: 'Photos kept with the flats you star',
					body: 'Listing photos show right in the app, and stay saved with the flats you star.'
				}
			]
		},
		later: {
			label: 'Later',
			items: [
				{
					title: 'Notifications',
					body: 'A notice on your computer when something new turns up, and if you like, an email to your own inbox.'
				},
				{
					title: 'More portals',
					body: 'Each one checked first for what it asks of apps.'
				},
				{
					title: 'On another computer',
					body: 'Run the watching on one machine and connect to it from your other devices.'
				}
			]
		}
	},
	devlog: {
		heading: 'Devlog',
		intro: "How rentczecher gets made: what worked, what didn't and what I learned along the way.",
		writtenInEnglish: 'Posts are written in English.',
		allPosts: 'All posts',
		read: 'Read',
		minutesToRead: (minutes) => `${minutes} min read`
	},
	faq: {
		heading: 'Questions',
		items: [
			{
				question: 'Is it really free?',
				answer: ['Yes. No subscription, no ads, no paid tier.']
			},
			{
				question: 'Which portals does it watch?',
				answer: [
					'RE/MAX, Bezrealitky and Sreality. RE/MAX is on from the start. Sreality and Bezrealitky are off by default, and you turn them on yourself in a profile after seeing what the portal asks. More portals will follow, each one checked first for what it asks of apps. rentczecher is not affiliated with, endorsed by or connected to any of these portals.'
				]
			},
			{
				question: 'Does it watch while my computer is off?',
				answer: [
					'No. It checks the portals when you press Run scan, with your computer on and the app open. Scans in the background are on the way. Whatever appeared in the meantime shows up on your next scan.'
				]
			},
			{
				question: 'Is the code really open?',
				answer: [
					'Yes, all of it is on ',
					{ text: 'GitHub', href: REPO_URL },
					' under the GPL-3.0 licence. Report bugs and ideas via ',
					{ text: 'Issues', href: ISSUES_URL },
					'.'
				]
			},
			{
				question: 'Why do Windows and macOS warn me?',
				answer: [
					'The app is not code-signed yet. On Windows, choose ',
					{ uiLabel: 'More info' },
					', then ',
					{ uiLabel: 'Run anyway' },
					'. A signed Windows installer is on the way. ',
					"On macOS, signing requires Apple's developer program, which costs €99 a year. I don't earn anything from the app, so I have no reason to spend that. You can still run the app, it just takes a little more work. Open ",
					{ uiLabel: 'System Settings' },
					' → ',
					{ uiLabel: 'Privacy & Security' },
					' and choose ',
					{ uiLabel: 'Open Anyway' },
					' next to rentczecher.'
				]
			},
			{
				question: "Who's behind it?",
				answer: [
					"My name is Matěj and I study computer science at Matfyz, Charles University's Faculty of Mathematics and Physics. I build this project in my free time, for free. If you like, you can ",
					{ text: 'support the project', href: SUPPORT_URL },
					". I'm grateful for any support, it helps keep the project alive."
				]
			}
		]
	},
	footer: {
		label: 'Links',
		credit:
			'Made by Matěj Schrödl. An independent open-source project, not affiliated with any real-estate portal.',
		operators: 'For portal operators',
		privacyPolicy: 'Privacy policy',
		support: 'Say thanks'
	},
	operators: {
		title: 'For portal operators',
		intro: 'If you came here from a User-Agent header in your logs, this is what rentczecher is and how it reads your site.',
		whatHeading: 'What it is',
		whatItIs: [
			'A free, open-source desktop app, licensed GPL-3.0-or-later.',
			'One person runs it on their own computer for their own home search.',
			'It has no server and no accounts, and users share no data with each other.',
			'It never republishes listings, stores no advert descriptions and links every listing back to its posting.'
		],
		howHeading: 'How it reads your site',
		userAgentIntro: 'It names itself in every request with this User-Agent:',
		howItReads: [
			"It reads only its user's saved searches, when its user starts a scan.",
			'It reads the result pages of a search, with a pause between pages and a cap on how many pages one search reads.',
			"After a scan it downloads each new listing's main photo. It opens an advert's own page, and fetches the listing's other photos, only when its user opens or stars that listing in the app, and only once.",
			'It uses no proxies, no rotating identities and no CAPTCHA or firewall bypass. If a portal refuses it, it does not try to get past the refusal.',
			'A portal whose terms or robots.txt ask automated clients to stay away is off by default.'
		],
		contactHeading: 'Contact',
		contact: [
			'If you have any concern about how rentczecher uses your portal, email me at ',
			{ text: CONTACT_EMAIL, href: `mailto:${CONTACT_EMAIL}` },
			'. Every such message gets a quick answer.'
		],
		notAffiliated: 'rentczecher is not affiliated with, endorsed by or connected to any real-estate portal.'
	},
	privacyPolicy: {
		title: 'Privacy policy',
		intro: 'rentczecher collects no personal data. This page lists every connection the app and this website make, so you can see exactly where your data goes.',
		keepsHeading: 'What the app keeps',
		keeps: [
			"Your profiles, saved and hidden listings, photos and price history are stored only on your computer, in the app's own data folder.",
			'There is no account, no server, no analytics, no crash reporting and no tracking. Nothing is ever sent to the author.',
			'Uninstalling the app and deleting its data folder removes everything it kept.',
			'You can save chosen profiles to a file, to add them on another computer. The file holds your searches and their preferences, never listings, and stays wherever you save it, even after the app is uninstalled.'
		],
		connectionsHeading: 'Who the app talks to',
		connectionsIntro: 'The app connects only to the services below, each for the one purpose listed. Each of them sees your IP address, as any website you visit does.',
		connections: [
			"The real-estate portals you turn on, and their image servers. When you run a scan it reads your saved searches and downloads each new listing's main photo. It reads a listing's advert and its other photos when you open or star it.",
			"OpenStreetMap's tile server (tile.openstreetmap.org), to draw street maps.",
			'Public OpenStreetMap Overpass servers (overpass-api.de, overpass.private.coffee, overpass.kumi.systems), to find nearby places such as shops or stops. They receive the map area around a listing and the kinds of places to look for, nothing else.',
			"GitHub (github.com, with downloads served from githubusercontent.com), where the app's releases are published. When the app starts and once a day after that, it asks whether a newer version is out, and it downloads one only when you choose to update. GitHub counts each check and download, so the author sees how often the app checks, but not who checked.",
			"A link to an advert, Mapy.com or Google Maps opens in your web browser, and from there that site's own privacy policy applies."
		],
		siteHeading: 'This website',
		site: [
			'rentczecher.cz is a static site hosted on GitHub Pages. It sets no cookies and runs no analytics.',
			"GitHub, as the host, may log technical data such as your IP address, under GitHub's own privacy statement.",
			'Your choice of light or dark theme is remembered in your browser only.'
		],
		contactHeading: 'Contact',
		contact: [
			'Questions about privacy go to ',
			{ text: CONTACT_EMAIL, href: `mailto:${CONTACT_EMAIL}` },
			'.'
		],
		updated: 'Last updated on 31 October 2026.'
	}
};
