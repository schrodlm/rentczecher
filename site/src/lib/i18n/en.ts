import type { Messages } from './messages';
import { ISSUES_URL, REPO_URL, SUPPORT_URL } from '$lib/links';

export const en: Messages = {
	meta: {
		title: 'rentczecher',
		description:
			"rentczecher keeps an eye on the major Czech real-estate portals and shows you only what's actually new. Price drops included. Free and open source."
	},
	topbar: 'rentczecher is open source. All the code is on GitHub, a star is always appreciated →',
	nav: {
		label: 'Main',
		roadmap: 'Roadmap',
		faq: 'FAQ'
	},
	languageLabel: 'Language',
	theme: {
		toDark: 'Switch to dark mode',
		toLight: 'Switch to light mode'
	},
	roadmap: {
		heading: "What's coming",
		intro: 'The plan follows what people need. Missing something? Say so on GitHub.',
		suggest: 'Suggest a feature',
		inProgress: {
			label: 'In progress',
			items: [
				{
					title: 'Searches inside the app',
					body: 'Create, edit and delete your searches in the app, and set your favourite listings aside.'
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
					title: 'An easy first start',
					body: 'Set up email and your first search in the app, without editing config files.'
				},
				{
					title: 'More real-estate portals',
					body: 'Reality.iDNES.cz comes first, the second largest Czech portal.'
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
					'RE/MAX, Bezrealitky and Sreality. RE/MAX is on from the start. Sreality and Bezrealitky are off by default, and you turn them on yourself in a profile after seeing what the portal asks. More portals will follow, with iDNES planned first. rentczecher is not affiliated with, endorsed by or connected to any of these portals.'
				]
			},
			{
				question: 'Does it watch while my computer is off?',
				answer: [
					'No, it watches while the app is running, at the interval you set. Once you start it again, it catches up on what appeared in the meantime.'
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
				question: 'Why does macOS warn me?',
				answer: [
					"Releasing an app properly on macOS requires Apple's developer program, which costs €99 a year. I don't earn anything from the app, so I have no reason to spend that. You can still run the app, it just takes a little more work. Open ",
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
	}
};
