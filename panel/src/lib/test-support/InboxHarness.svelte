<script lang="ts">
	import type { ListingModel, PostingPricesModel } from '$lib/api/client';
	import Inbox from '$lib/components/Inbox.svelte';
	import type { ScoringPreferences } from '$lib/scoring/score';

	/* Holds listings the way the inbox page does: viewing and starring change
	them in place, while marking all viewed loads them afresh. */
	let {
		listings,
		preferences,
		onview,
		onfavourite,
		loadPriceHistory = async () => []
	}: {
		listings: ListingModel[];
		preferences: ScoringPreferences | null;
		onview: (listingId: string) => void;
		onfavourite: (listingId: string, favourite: boolean) => void;
		loadPriceHistory?: (listingId: string) => Promise<PostingPricesModel[]>;
	} = $props();

	const NOW = '2026-10-11T10:00:00Z';

	// svelte-ignore state_referenced_locally
	let held = $state(listings);

	function view(listingId: string): void {
		onview(listingId);
		const listing = held.find((each) => each.id === listingId);
		if (listing !== undefined) listing.viewed_at = NOW;
	}

	function favourite(listingId: string, on: boolean): void {
		onfavourite(listingId, on);
		const listing = held.find((each) => each.id === listingId);
		if (listing === undefined) return;
		listing.favourited_at = on ? NOW : null;
		listing.viewed_at = listing.viewed_at ?? NOW;
	}

	function markAllViewedAndReload(listingIds: string[]): void {
		held = held.map((listing) =>
			listingIds.includes(listing.id) ? { ...listing, viewed_at: listing.viewed_at ?? NOW } : listing
		);
	}
</script>

<Inbox
	listings={held}
	{preferences}
	onview={view}
	onfavourite={favourite}
	onmarkallviewed={markAllViewedAndReload}
	{loadPriceHistory}
/>
