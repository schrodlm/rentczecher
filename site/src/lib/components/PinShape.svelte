<script lang="ts" module>
	export type PinKind = 'flat' | 'house' | 'cottage';
</script>

<script lang="ts">
	let { kind }: { kind: PinKind } = $props();
</script>

<!-- Drawn standing on the origin, so a translate places the pin's foot on its spot. -->
{#if kind === 'flat'}
	<path d="M-10,0L-10,-26L10,-26L10,0Z" />
	<rect x="-6" y="-22" width="4" height="4" />
	<rect x="2" y="-22" width="4" height="4" />
	<rect x="-6" y="-15" width="4" height="4" />
	<rect x="2" y="-15" width="4" height="4" />
	<rect x="-2" y="-7" width="4" height="7" />
{:else if kind === 'house'}
	<path d="M-12,0L-12,-13L0,-24L12,-13L12,0Z" />
	<rect x="-3" y="-9" width="6" height="9" />
{:else if kind === 'cottage'}
	<path d="M-14,0L0,-27L14,0Z" />
	<rect x="-3" y="-10" width="6" height="10" />
	<rect x="-2" y="-19" width="4" height="4" />
{/if}
