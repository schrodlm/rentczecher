<script lang="ts">
	import type { TrackedPropertyModel, PostingPricesModel } from '$lib/api/client';
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
		listings: TrackedPropertyModel[];
		preferences: ScoringPreferences | null;
		onview: (propertyId: string) => void;
		onfavourite: (propertyId: string, favourite: boolean) => void;
		loadPriceHistory?: (propertyId: string) => Promise<PostingPricesModel[]>;
	} = $props();

	const NOW = '2026-10-11T10:00:00Z';

	// svelte-ignore state_referenced_locally
	let held = $state(listings);

	function view(propertyId: string): void {
		onview(propertyId);
		const listing = held.find((each) => each.id === propertyId);
		if (listing !== undefined) listing.viewed_at = NOW;
	}

	function favourite(propertyId: string, on: boolean): void {
		onfavourite(propertyId, on);
		const listing = held.find((each) => each.id === propertyId);
		if (listing === undefined) return;
		listing.favourited_at = on ? NOW : null;
		listing.viewed_at = listing.viewed_at ?? NOW;
	}

	function markAllViewedAndReload(propertyIds: string[]): void {
		held = held.map((listing) =>
			propertyIds.includes(listing.id) ? { ...listing, viewed_at: listing.viewed_at ?? NOW } : listing
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
