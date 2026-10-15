<script lang="ts" module>
	export type FeatureIllustrationKind =
		| 'onlyNew'
		| 'oneList'
		| 'memory'
		| 'backToPortal'
		| 'privacy'
		| 'free';
</script>

<script lang="ts">
	let { kind }: { kind: FeatureIllustrationKind } = $props();
</script>

<svg viewBox="0 0 160 100" aria-hidden="true">
	{#if kind === 'onlyNew'}
		<rect x="28" y="38" width="84" height="52" rx="6" class="s-old" />
		<rect x="36" y="28" width="84" height="52" rx="6" class="s-old2" />
		<g class="a-new">
			<rect x="44" y="18" width="84" height="52" rx="6" class="s-card" />
			<rect x="53" y="27" width="30" height="24" rx="3" class="s-amber" />
			<rect x="89" y="29" width="30" height="5" rx="2.5" class="s-ink" />
			<rect x="89" y="39" width="20" height="5" rx="2.5" class="s-muted" />
			<rect x="53" y="57" width="44" height="5" rx="2.5" class="s-muted" />
		</g>
		<g class="a-pop">
			<circle cx="128" cy="20" r="12" class="s-amber" />
			<path d="M122.5 20l3.8 3.8 7-7.5" class="st-dark" />
		</g>
	{:else if kind === 'oneList'}
		<g class="a-in a-in1">
			<rect x="10" y="12" width="30" height="20" rx="4" class="s-card" />
			<rect x="15" y="17" width="10" height="10" rx="2" class="s-amber" />
		</g>
		<g class="a-in a-in2">
			<rect x="10" y="40" width="30" height="20" rx="4" class="s-card" />
			<rect x="15" y="45" width="10" height="10" rx="2" class="s-amber" />
		</g>
		<g class="a-in a-in3">
			<rect x="10" y="68" width="30" height="20" rx="4" class="s-card" />
			<rect x="15" y="73" width="10" height="10" rx="2" class="s-amber" />
		</g>
		<path d="M66 50h14" class="st-line" />
		<path d="M75 45l5 5-5 5" class="st-line" />
		<g class="a-tray">
			<path d="M96 30h50l8 22v24a4 4 0 0 1-4 4H92a4 4 0 0 1-4-4V52z" class="s-card" />
			<path d="M88 52h18l5 9h20l5-9h18" class="st-line" />
			<circle cx="148" cy="30" r="9" class="s-olive" />
			<text x="148" y="34" text-anchor="middle" class="t-badge">1</text>
		</g>
	{:else if kind === 'memory'}
		<rect x="22" y="10" width="116" height="80" rx="8" class="s-card" />
		<circle cx="42" cy="30" r="8" class="s-old" />
		<path d="M38 30l3 3 5.5-6" class="st-olive a-tick" />
		<rect x="58" y="27" width="60" height="6" rx="3" class="s-muted" />
		<circle cx="42" cy="50" r="8" class="s-old" />
		<path d="M38 50l3 3 5.5-6" class="st-olive a-tick a-tick2" />
		<rect x="58" y="47" width="46" height="6" rx="3" class="s-muted" />
		<circle cx="42" cy="70" r="8" class="s-old" />
		<path d="M38 70l3 3 5.5-6" class="st-olive a-tick a-tick3" />
		<rect x="58" y="67" width="54" height="6" rx="3" class="s-muted" />
	{:else if kind === 'backToPortal'}
		<rect x="10" y="28" width="60" height="46" rx="6" class="s-card" />
		<rect x="16" y="34" width="20" height="16" rx="3" class="s-amber" />
		<rect x="40" y="36" width="24" height="4" rx="2" class="s-ink" />
		<rect x="16" y="58" width="40" height="4" rx="2" class="s-muted" />
		<g class="a-nudge">
			<path d="M76 51h20" class="st-line" />
			<path d="M91 46l5 5-5 5" class="st-line" />
		</g>
		<rect x="104" y="18" width="50" height="64" rx="6" class="s-card" />
		<path d="M104 30h50" class="st-line" />
		<circle cx="111" cy="24" r="2" class="s-muted" />
		<circle cx="118" cy="24" r="2" class="s-muted" />
		<rect x="110" y="36" width="38" height="18" rx="3" class="s-amber" />
		<rect x="110" y="60" width="30" height="4" rx="2" class="s-ink" />
		<rect x="110" y="68" width="22" height="4" rx="2" class="s-muted" />
	{:else if kind === 'privacy'}
		<g class="a-float">
			<path
				d="M58 30a10 10 0 0 1 19-5 9 9 0 0 1 15 7h1a7 7 0 0 1 0 14H58a8 8 0 0 1 0-16z"
				class="st-dash"
			/>
			<path d="M54 14l46 40" class="st-cross" />
		</g>
		<rect x="42" y="56" width="76" height="34" rx="4" class="s-card" />
		<path d="M30 92h100" class="st-line" />
		<rect x="72" y="70" width="16" height="13" rx="2" class="s-amber" />
		<path d="M75 70v-4a5 5 0 0 1 10 0v4" class="st-amber a-lock" />
	{:else if kind === 'free'}
		<g class="a-swing">
			<path d="M44 30h58l22 22-22 22H44a6 6 0 0 1-6-6V36a6 6 0 0 1 6-6z" class="s-amber" />
			<circle cx="104" cy="52" r="4.5" class="s-bg" />
			<text x="70" y="59" text-anchor="middle" class="t-price">0 Kč</text>
		</g>
		<path d="M108.5 52C122 52 132 40 138 26" class="st-line" />
	{/if}
</svg>

<style>
	svg {
		width: 100%;
		max-width: 220px;
		height: auto;
		display: block;
		overflow: visible;
	}

	svg :global(*) {
		transform-box: fill-box;
	}

	.s-card {
		fill: var(--surface);
		stroke: var(--line-strong);
		stroke-width: 1.5;
	}
	.s-old {
		fill: var(--line);
	}
	.s-old2 {
		fill: var(--line-strong);
		opacity: 0.55;
	}
	.s-amber {
		fill: var(--amber);
	}
	.s-ink {
		fill: var(--text);
	}
	.s-muted {
		fill: var(--line-strong);
	}
	.s-olive {
		fill: var(--olive);
	}
	.s-bg {
		fill: var(--bg);
	}
	.st-dark {
		fill: none;
		stroke: var(--on-amber);
		stroke-width: 2.5;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.st-line {
		fill: none;
		stroke: var(--line-strong);
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.st-olive {
		fill: none;
		stroke: var(--olive);
		stroke-width: 2.5;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.st-amber {
		fill: none;
		stroke: var(--amber);
		stroke-width: 3;
		stroke-linecap: round;
	}
	.st-cross {
		fill: none;
		stroke: var(--muted);
		stroke-width: 3;
		stroke-linecap: round;
	}
	.st-dash {
		fill: none;
		stroke: var(--line-strong);
		stroke-width: 2;
		stroke-dasharray: 5 4;
	}
	.t-badge {
		fill: var(--on-olive);
		font: 800 11px system-ui, sans-serif;
	}
	.t-price {
		fill: var(--on-amber);
		font: 800 17px system-ui, sans-serif;
	}

	.a-new {
		animation: anew 4s infinite;
	}
	@keyframes anew {
		0% {
			opacity: 0;
			transform: translateX(26px);
		}
		12%,
		82% {
			opacity: 1;
			transform: none;
		}
		96%,
		100% {
			opacity: 0;
			transform: translateY(-6px);
		}
	}

	.a-pop {
		transform-origin: 50% 50%;
		animation: apop 4s infinite;
	}
	@keyframes apop {
		0%,
		14% {
			transform: scale(0);
		}
		20% {
			transform: scale(1.2);
		}
		24%,
		82% {
			transform: scale(1);
		}
		92%,
		100% {
			transform: scale(0);
		}
	}

	.a-in {
		animation: ain 4.5s infinite;
	}
	.a-in1 {
		--dy: 32px;
	}
	.a-in2 {
		--dy: 4px;
		animation-delay: 0.25s;
	}
	.a-in3 {
		--dy: -24px;
		animation-delay: 0.5s;
	}
	@keyframes ain {
		0%,
		15% {
			opacity: 1;
			transform: none;
		}
		50% {
			opacity: 0;
			transform: translate(84px, var(--dy)) scale(0.6);
		}
		51%,
		70% {
			opacity: 0;
			transform: none;
		}
		85%,
		100% {
			opacity: 1;
			transform: none;
		}
	}

	.a-tray {
		transform-origin: 50% 100%;
		animation: atray 4.5s infinite;
	}
	@keyframes atray {
		0%,
		48% {
			transform: none;
		}
		55% {
			transform: scale(1.06);
		}
		62%,
		100% {
			transform: none;
		}
	}

	.a-tick {
		stroke-dasharray: 14;
		stroke-dashoffset: 14;
		animation: atick 4.5s infinite;
	}
	.a-tick2 {
		animation-delay: 0.6s;
	}
	.a-tick3 {
		animation-delay: 1.2s;
	}
	@keyframes atick {
		0%,
		8% {
			stroke-dashoffset: 14;
		}
		20%,
		80% {
			stroke-dashoffset: 0;
		}
		92%,
		100% {
			stroke-dashoffset: 14;
		}
	}



	.a-nudge {
		animation: anudge 2.4s ease-in-out infinite;
	}
	@keyframes anudge {
		0%,
		100% {
			transform: translateX(0);
		}
		50% {
			transform: translateX(4px);
		}
	}

	.a-float {
		animation: afloat 3.5s ease-in-out infinite;
	}
	@keyframes afloat {
		0%,
		100% {
			transform: translateY(0);
		}
		50% {
			transform: translateY(-5px);
		}
	}

	.a-lock {
		animation: alock 3.5s infinite;
	}
	@keyframes alock {
		0%,
		40% {
			transform: translateY(-3px);
		}
		50%,
		100% {
			transform: none;
		}
	}

	.a-swing {
		transform-origin: 94% 50%;
		animation: aswing 3s ease-in-out infinite;
	}
	@keyframes aswing {
		0%,
		100% {
			transform: rotate(-5deg);
		}
		50% {
			transform: rotate(5deg);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		svg :global(*) {
			animation: none !important;
		}
		.a-tick {
			stroke-dashoffset: 0;
		}
	}
</style>
