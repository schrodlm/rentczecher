<script lang="ts">
	import type { ListingModel } from '$lib/api/client';
	import Inbox from '$lib/components/Inbox.svelte';
	import type { ScoringPreferences } from '$lib/scoring/score';

	/* Holds listings the way the inbox page does and applies viewing and
	starring to them, so a test sees the rows move between sections. */
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

	// svelte-ignore state_referenced_locally
	let held = $state(listings);

	function view(listingId: string): void {
		onview(listingId);
		const listing = held.find((each) => each.id === listingId);
		if (listing !== undefined) listing.viewed_at = '2026-10-11T10:00:00Z';
	}

	function favourite(listingId: string, on: boolean): void {
		onfavourite(listingId, on);
		const listing = held.find((each) => each.id === listingId);
		if (listing === undefined) return;
		listing.favourited_at = on ? '2026-10-11T10:00:00Z' : null;
		listing.viewed_at = listing.viewed_at ?? '2026-10-11T10:00:00Z';
	}
</script>

<Inbox listings={held} {preferences} onview={view} onfavourite={favourite} onmarkallviewed={() => {}} />
