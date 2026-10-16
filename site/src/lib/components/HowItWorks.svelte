<script lang="ts">
	import Icon from './Icon.svelte';
	import type { Language } from '$lib/i18n';
	import type { HowStep, Messages } from '$lib/i18n/messages';

	let { t, lang }: { t: Messages; lang: Language } = $props();

	const steps: Array<{ screenshot: string; width: number; height: number; copy: HowStep }> = $derived([
		{ screenshot: 'search', width: 2112, height: 2448, copy: t.how.steps.search },
		{ screenshot: 'preferences', width: 2112, height: 1350, copy: t.how.steps.preferences },
		{ screenshot: 'inbox', width: 2880, height: 1800, copy: t.how.steps.inbox }
	]);

	let current = $state(0);

	function show(step: number) {
		current = (step + steps.length) % steps.length;
	}
</script>

<section id="how" class="container">
	<h2 class="section-heading">{t.how.heading}</h2>
	<div class="steps" role="group" aria-label={t.how.stepsLabel}>
		{#each steps as step, index (step.screenshot)}
			<button type="button" class="step" aria-current={index === current} onclick={() => show(index)}>
				<span class="number">{index + 1}</span>
				<span class="title">{step.copy.title}</span>
				<span class="body">{step.copy.body}</span>
			</button>
		{/each}
	</div>
	<div class="viewer">
		<div class="frame">
			<div class="track" style:transform="translateX({-100 * current}%)">
				{#each steps as step, index (step.screenshot)}
					<div class="slide" inert={index !== current}>
						<img
							class="light"
							src="/screenshots/{step.screenshot}-{lang}-light.webp"
							alt={step.copy.screenshotAlt}
							width={step.width}
							height={step.height}
							loading="lazy"
						/>
						<img
							class="dark"
							src="/screenshots/{step.screenshot}-{lang}-dark.webp"
							alt={step.copy.screenshotAlt}
							width={step.width}
							height={step.height}
							loading="lazy"
						/>
					</div>
				{/each}
			</div>
		</div>
		<button
			type="button"
			class="iconbtn arrow arrow-prev"
			aria-label={t.how.previous}
			onclick={() => show(current - 1)}><Icon name="chevron-left" size={22} /></button
		>
		<button
			type="button"
			class="iconbtn arrow arrow-next"
			aria-label={t.how.next}
			onclick={() => show(current + 1)}><Icon name="chevron-right" size={22} /></button
		>
	</div>
	<div class="dots">
		{#each steps as step, index (step.screenshot)}
			<button
				type="button"
				class="dot"
				aria-current={index === current}
				aria-label={step.copy.title}
				onclick={() => show(index)}><span></span></button
			>
		{/each}
	</div>
</section>

<style>
	section {
		padding-top: 80px;
		padding-bottom: 80px;
		display: flex;
		flex-direction: column;
		gap: 32px;
	}

	.steps {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
		gap: 16px;
	}

	.step {
		display: flex;
		flex-direction: column;
		gap: 8px;
		text-align: left;
		font: inherit;
		color: var(--text);
		background: transparent;
		border: 0;
		border-top: 3px solid var(--line-strong);
		padding: 18px 4px 6px;
		cursor: pointer;
		transition: border-color 0.3s;
	}

	.step:hover {
		border-top-color: var(--muted);
	}

	.step[aria-current='true'] {
		border-top-color: var(--olive);
	}

	.step:not([aria-current='true']) > span:nth-child(n + 2) {
		opacity: 0.7;
	}

	.number {
		font-size: 14px;
		font-weight: 800;
		color: var(--link);
	}

	.title {
		font-size: 21px;
		font-weight: 700;
	}

	.body {
		line-height: 1.5;
		color: var(--muted);
	}

	.viewer {
		position: relative;
	}

	/* One frame for every step, no taller than the screen. Each screenshot fits whole inside it. */
	.frame {
		aspect-ratio: 16 / 10;
		width: min(100%, calc(16 / 10 * 75svh));
		margin: 0 auto;
		overflow: hidden;
		border-radius: 12px;
		border: 1px solid var(--line);
		background: var(--bg);
		box-shadow: 0 10px 30px var(--shadow);
	}

	.track {
		display: flex;
		height: 100%;
		transition: transform 0.55s cubic-bezier(0.65, 0, 0.35, 1);
	}

	.slide {
		flex: 0 0 100%;
	}

	.slide img {
		width: 100%;
		height: 100%;
		object-fit: contain;
	}

	/* The screenshots follow the page theme: the visitor's choice first, the system one otherwise. */
	.light {
		display: block;
	}

	.dark {
		display: none;
	}

	@media (prefers-color-scheme: dark) {
		:global(:root:not([data-theme='light'])) .light {
			display: none;
		}

		:global(:root:not([data-theme='light'])) .dark {
			display: block;
		}
	}

	:global(:root[data-theme='dark']) .light {
		display: none;
	}

	:global(:root[data-theme='dark']) .dark {
		display: block;
	}

	.arrow {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		background: var(--surface);
		box-shadow: 0 4px 14px var(--shadow);
	}

	.arrow-prev {
		left: 16px;
	}

	.arrow-next {
		right: 16px;
	}

	.dots {
		display: flex;
		justify-content: center;
		gap: 6px;
	}

	.dot {
		width: 44px;
		height: 44px;
		border: 0;
		background: transparent;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0;
	}

	.dot > span {
		width: 10px;
		height: 10px;
		border-radius: 999px;
		background: var(--line-strong);
		transition:
			width 0.3s,
			background 0.3s;
	}

	.dot[aria-current='true'] > span {
		width: 28px;
		background: var(--olive);
	}

	@media (prefers-reduced-motion: reduce) {
		.track,
		.dot > span,
		.step {
			transition: none;
		}
	}
</style>
