// A uiLabel names something the reader finds on screen, such as a settings page or a button.
export type RichText = Array<string | { text: string; href: string } | { uiLabel: string }>;

export interface FaqItem {
	question: string;
	answer: RichText;
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
		roadmap: string;
		faq: string;
	};
	languageLabel: string;
	theme: {
		toDark: string;
		toLight: string;
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
		allPosts: string;
		read: string;
		minutesToRead: (minutes: number) => string;
	};
	faq: {
		heading: string;
		items: FaqItem[];
	};
}
