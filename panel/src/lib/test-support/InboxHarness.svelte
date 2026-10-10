<script lang="ts">
	import type { ListingModel } from '$lib/api/client';
	import Inbox from '$lib/components/Inbox.svelte';
	import type { ScoringPreferences } from '$lib/scoring/score';

	/* Holds listings the way the inbox page does: viewing and starring change
	them in place, while marking all viewed loads them afresh. */
	let {
		listings,
		preferences,
		onview,
		onfavourite
	}: {
		listings: ListingModel[];
		preferences: ScoringPreferences | null;
		onview: (listingId: string) => void;
		onfavourite: (listingId: string, favourite: boolean) => void;
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

	function markAllViewedAndReload(): void {
		held = held.map((listing) => ({ ...listing, viewed_at: listing.viewed_at ?? NOW }));
	}
</script>

<Inbox listings={held} {preferences} onview={view} onfavourite={favourite} onmarkallviewed={markAllViewedAndReload} />
