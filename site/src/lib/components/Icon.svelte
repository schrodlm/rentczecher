<script lang="ts">
	type IconName = 'branch' | 'sun' | 'moon';

	let { name, size = 20 }: { name: IconName; size?: number } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="2"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	{#if name === 'branch'}
		<circle cx="6" cy="5" r="2.5" /><circle cx="6" cy="19" r="2.5" /><circle cx="18" cy="7" r="2.5" />
		<path d="M6 7.5v9" /><path d="M18 9.5c0 4-4 4.5-9.5 7.5" />
	{:else if name === 'sun'}
		<circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" />
		<path d="m4.9 4.9 1.4 1.4" /><path d="m17.7 17.7 1.4 1.4" /><path d="M2 12h2" />
		<path d="M20 12h2" /><path d="m4.9 19.1 1.4-1.4" /><path d="m17.7 6.3 1.4-1.4" />
	{:else if name === 'moon'}
		<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />
	{/if}
</svg>
