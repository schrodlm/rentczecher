<script lang="ts">
	type IconName =
		| 'branch'
		| 'code'
		| 'download'
		| 'star'
		| 'alert'
		| 'book'
		| 'heart'
		| 'sun'
		| 'moon';

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
	{:else if name === 'code'}
		<path d="m8 7-5 5 5 5" /><path d="m16 7 5 5-5 5" />
	{:else if name === 'download'}
		<path d="M12 4v11" /><path d="m7 10 5 5 5-5" /><path d="M5 20h14" />
	{:else if name === 'star'}
		<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" />
	{:else if name === 'alert'}
		<circle cx="12" cy="12" r="9" /><path d="M12 8v5" /><path d="M12 16.5v.01" />
	{:else if name === 'book'}
		<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" /><path d="M5 17a3 3 0 0 1 3-3h11" />
	{:else if name === 'heart'}
		<path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.2a4.3 4.3 0 0 1 7.5 2.6C19.5 15.4 12 20 12 20z" />
	{:else if name === 'sun'}
		<circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" />
		<path d="m4.9 4.9 1.4 1.4" /><path d="m17.7 17.7 1.4 1.4" /><path d="M2 12h2" />
		<path d="M20 12h2" /><path d="m4.9 19.1 1.4-1.4" /><path d="m17.7 6.3 1.4-1.4" />
	{:else if name === 'moon'}
		<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />
	{/if}
</svg>
