<!-- PROTOTYPE, throwaway. Round 1's place picker, kept so its variants still build. -->
<script lang="ts">
	import Picker from '../PlacePicker.svelte';
	import type { NamedPlace, PlaceSearch } from './draft.svelte';

	let {
		search,
		within = null,
		placeholder,
		onpick
	}: { search: PlaceSearch; within?: NamedPlace | null; placeholder?: string; onpick: (place: NamedPlace) => void } = $props();
</script>

<Picker search={(q) => search(q, within)} {placeholder} {onpick} />
