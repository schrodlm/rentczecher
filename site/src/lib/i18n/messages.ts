// A uiLabel names something the reader finds on screen, such as a settings page or a button.
export type RichText = Array<string | { text: string; href: string } | { uiLabel: string }>;

export interface FaqItem {
	question: string;
	answer: RichText;
}

export interface FeatureCard {
	title: string;
	body: string;
}

export interface HowStep {
	title: string;
	body: string;
	screenshotAlt: string;
}

export interface RoadmapItem {
	title: string;
	body: string;
}

export interface RoadmapColumn {
	label: string;
	items: RoadmapItem[];
}

export interface Messages {
	meta: {
		title: string;
		description: string;
	};
	topbar: string;
	nav: {
		label: string;
		features: string;
		how: string;
		roadmap: string;
		devlog: string;
		faq: string;
	};
	languageLabel: string;
	theme: {
		toDark: string;
		toLight: string;
	};
	hero: {
		badge: string;
		lead: string;
		kinds: [string, string, string];
		kindsLabel: string;
		tail: string;
		promise: string;
		intro: string;
		download: string;
		source: string;
		freeVersion: (version: string) => string;
		platforms: string;
		mapLabel: string;
		newBadge: string;
		newAgo: string;
		newTitle: string;
		newDetail: string;
		dropBadge: string;
		dropAgo: string;
		dropTitle: string;
		dropDetail: string;
		dropAmount: string;
	};
	portals: {
		label: string;
		heading: string;
		defaults: string;
		more: string;
		notAffiliated: string;
	};
	features: {
		heading: string;
		intro: string;
		cards: {
			onlyNew: FeatureCard;
			oneList: FeatureCard;
			memory: FeatureCard;
			backToPortal: FeatureCard;
			privacy: FeatureCard;
			free: FeatureCard;
		};
	};
	how: {
		heading: string;
		stepsLabel: string;
		previous: string;
		next: string;
		steps: {
			search: HowStep;
			preferences: HowStep;
			inbox: HowStep;
		};
	};
	privacy: {
		heading: string;
		body: string;
	};
	openSource: {
		chip: string;
		heading: string;
		body: string;
		star: string;
		reportBug: string;
		repoDescription: string;
		licence: string;
		authorHeading: string;
		authorBody: string;
		support: string;
	};
	download: {
		heading: string;
		version: string;
		free: string;
		allReleases: string;
		button: string;
		windows: string;
		macos: string;
		linux: string;
		firstLaunchWarning: string;
		whatToDo: string;
		buildYourself: string;
		readme: string;
	};
	roadmap: {
		heading: string;
		intro: string;
		suggest: string;
		inProgress: RoadmapColumn;
		next: RoadmapColumn;
		later: RoadmapColumn;
	};
	devlog: {
		heading: string;
		intro: string;
		writtenInEnglish: string;
		allPosts: string;
		read: string;
		minutesToRead: (minutes: number) => string;
	};
	faq: {
		heading: string;
		items: FaqItem[];
	};
	footer: {
		label: string;
		credit: string;
		operators: string;
		support: string;
	};
	operators: {
		title: string;
		intro: string;
		whatHeading: string;
		whatItIs: string[];
		howHeading: string;
		userAgentIntro: string;
		howItReads: string[];
		contactHeading: string;
		contact: RichText;
		notAffiliated: string;
	};
}
