// A uiLabel names something the reader finds on screen, such as a settings page or a button.
export type RichText = Array<string | { text: string; href: string } | { uiLabel: string }>;

export interface FaqItem {
	question: string;
	answer: RichText;
}

export interface Messages {
	meta: {
		title: string;
		description: string;
	};
	topbar: string;
	nav: {
		label: string;
		faq: string;
	};
	languageLabel: string;
	theme: {
		toDark: string;
		toLight: string;
	};
	faq: {
		heading: string;
		items: FaqItem[];
	};
}
