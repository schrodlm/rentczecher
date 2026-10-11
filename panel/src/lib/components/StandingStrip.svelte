<script lang="ts">
	import type { Standing } from '$lib/property-detail';

	/* One fact of a listing on a strip from the profile's lowest to its
	highest: the other listings as dots, the middle as a tick, the listing
	itself as a marker, with its value and what the strip says in words. */
	let {
		standing,
		label,
		format,
		saying
	}: {
		standing: Standing;
		label: string;
		format: (value: number) => string;
		saying: string;
	} = $props();

	function along(value: number): number {
		const span = standing.highest - standing.lowest;
		return span === 0 ? 50 : ((value - standing.lowest) / span) * 100;
	}
</script>

<div class="standing-strip">
	<div class="standing-strip__head">
		<b>{label}</b>
		<span class="standing-strip__own">{format(standing.own)}</span>
	</div>
	<div class="standing-strip__track" aria-hidden="true">
		<i class="standing-strip__middle" style:left="{along(standing.middle)}%"></i>
		{#each standing.others as value, index (index)}
			<i class="standing-strip__other" style:left="{along(value)}%"></i>
		{/each}
		<i class="standing-strip__marker" style:left="{along(standing.own)}%"></i>
	</div>
	<div class="standing-strip__ends" aria-hidden="true">
		<span>{format(standing.lowest)}</span>
		<span>{format(standing.highest)}</span>
	</div>
	<p class="standing-strip__saying">{saying}</p>
</div>

<style>
	.standing-strip {
		display: flex;
		flex-direction: column;
		gap: var(--space-1);
	}

	.standing-strip__head {
		display: flex;
		justify-content: space-between;
		font-size: 0.875rem;
	}

	.standing-strip__own {
		font-weight: 700;
	}

	.standing-strip__track {
		position: relative;
		height: 1rem;
		margin: 0 0.5rem;
	}

	.standing-strip__track::before {
		content: '';
		position: absolute;
		top: 50%;
		left: 0;
		right: 0;
		height: 2px;
		border-radius: 1px;
		background: var(--color-line);
		transform: translateY(-50%);
	}

	.standing-strip__track i {
		position: absolute;
		top: 50%;
		transform: translate(-50%, -50%);
	}

	.standing-strip__middle {
		width: 2px;
		height: 0.875rem;
		background: var(--color-bronze);
		opacity: 0.6;
	}

	.standing-strip__other {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: color-mix(in srgb, var(--color-bronze) 45%, var(--color-card));
	}

	.standing-strip__marker {
		z-index: 1;
		width: 0.875rem;
		height: 0.875rem;
		border: 2px solid var(--color-card);
		border-radius: 50%;
		background: var(--color-amber);
		box-shadow: 0 0 0 1px var(--color-amber);
	}

	.standing-strip__ends {
		display: flex;
		justify-content: space-between;
		color: var(--color-bronze);
		font-size: 0.6875rem;
	}

	.standing-strip__saying {
		margin: 0;
		font-size: 0.8125rem;
	}
</style>
