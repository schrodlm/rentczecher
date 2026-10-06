<!-- PROTOTYPE, throwaway. The profile editor, mounted on the inbox page
through ?editor=new or ?editor=<profile id>. Round 1's variants A, B and C
stay in this folder for reference. Saving and deleting only show the
request that would be sent. Place search is real when the engine is
reachable. -->
<script lang="ts">
	import { page } from '$app/state';
	import type { ProfileModel } from '$lib/api/client';
	import { sidecarConnection } from '$lib/api/connection';
	import ProfileEditorWindow from './ProfileEditorWindow.svelte';
	import PrototypeSwitcher from '../PrototypeSwitcher.svelte';
	import { draftFromProfile, emptyDraft, request, type NamedPlace } from './draft.svelte';

	let { profile, onclose }: { profile: ProfileModel | null; onclose: () => void } = $props();

	const editing = $derived(profile !== null);

	const MAP_MODES = { A: 'smooth', B: 'spotlight', C: 'free' } as const;
	const mapMode = $derived(MAP_MODES[(page.url.searchParams.get('map') ?? 'A') as keyof typeof MAP_MODES] ?? 'smooth');

	// ?demo=1 prefills a new profile so every section has something to show.
	function demoDraft() {
		const d = emptyDraft();
		d.name = 'Praha 7 byty';
		d.place = { kind: 'obvod', code: 78, name: 'Praha 7', obec: 'Praha', okres: null };
		d.maxPrice = 30000;
		d.minSize = 45;
		d.layouts = ['2+kk', '2+1', '3+kk'];
		d.maxGoodPrice = 22500;
		d.idealSize = 70;
		d.preferredDispositions = ['3+kk', '2+kk'];
		d.preferredPlaces = [{ kind: 'cast_obce', code: 490067, name: 'Holešovice', obec: 'Praha', okres: null }];
		d.importance = { price: 4, pricePerM2: 0, size: 2, land: 0, layout: 3, place: 2 };
		return d;
	}

	// svelte-ignore state_referenced_locally
	let draft = $state(profile ? draftFromProfile(profile) : page.url.searchParams.has('demo') ? demoDraft() : emptyDraft());
	let sent = $state<string | null>(null);

	const pending = $derived(JSON.stringify(request(draft, profile?.id ?? null), null, 2));

	const FALLBACK: NamedPlace[] = [
		{ kind: 'obvod', code: 78, name: 'Praha 7', obec: 'Praha', okres: null },
		{ kind: 'cast_obce', code: 490067, name: 'Holešovice', obec: 'Praha', okres: null },
		{ kind: 'okres', code: 3401, name: 'Domažlice', obec: null, okres: null },
		{ kind: 'obec', code: 553425, name: 'Domažlice', obec: null, okres: 'Domažlice' }
	];

	let connection: Promise<{ baseUrl: string; token: string } | null> | null = null;

	async function search(query: string, within: NamedPlace | null, kinds?: string[]): Promise<NamedPlace[]> {
		connection ??= sidecarConnection().catch(() => null);
		const engine = await connection;
		if (engine === null) {
			const folded = query.toLocaleLowerCase('cs');
			return FALLBACK.filter(
				(p) => (p.name ?? '').toLocaleLowerCase('cs').startsWith(folded) && (!kinds || kinds.includes(p.kind))
			);
		}
		const url = new URL('/v1/places', engine.baseUrl);
		url.searchParams.set('q', query);
		if (within) url.searchParams.set('within', `${within.kind}:${within.code}`);
		for (const kind of kinds ?? []) url.searchParams.append('kind', kind);
		const response = await fetch(url, { headers: { Authorization: `Bearer ${engine.token}` } });
		return response.ok ? response.json() : [];
	}

	function onsave(): void {
		sent = pending;
	}

	function ondelete(): void {
		sent = `DELETE /v1/profiles/${profile?.id}`;
	}
</script>

<ProfileEditorWindow bind:draft {editing} {search} {mapMode} {onsave} oncancel={onclose} {ondelete} />

<PrototypeSwitcher param="map" variants={['A', 'B', 'C']} labels={{ A: 'Click and fade', B: 'Spotlight', C: 'Free zoom' }} />

<details class="proto-state">
	<summary>Prototype: the request {sent ? 'sent' : 'so far'}</summary>
	<pre>{sent ?? pending}</pre>
</details>


<style>
	.proto-state {
		position: fixed;
		left: 1rem;
		bottom: 1rem;
		z-index: 99;
		max-width: 26rem;
		max-height: 50vh;
		overflow: auto;
		background: #111;
		color: #cfc;
		font: 0.75rem ui-monospace, monospace;
		border-radius: 0.5rem;
		padding: 0.4rem 0.7rem;
		opacity: 0.92;
	}
	.proto-state pre {
		margin: 0.4rem 0 0;
		white-space: pre-wrap;
	}
</style>
