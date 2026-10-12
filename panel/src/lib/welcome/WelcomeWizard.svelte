<script lang="ts">
	import { onMount } from 'svelte';
	import logo from '$lib/assets/logo.svg';
	import Flag from '$lib/components/Flag.svelte';
	import ThemeIcon from '$lib/components/ThemeIcon.svelte';
	import { getTranslatorContext } from '$lib/i18n/context';
	import { applyTheme, themeName } from '$lib/theme';
	import { LANGUAGE_NAMES, LANGUAGES, THEMES, type Language, type Theme, type UserConfig } from '$lib/user-config';
	import ProfileShowcase from './ProfileShowcase.svelte';

	/* The three steps of the first run over the dimmed app: the language, the
	theme, and a look at what a profile does. Picking another language reloads
	the app in it, with the choices so far carried in the address, since
	nothing is saved until the last step. */
	let {
		theme: startingTheme,
		oncomplete
	}: {
		theme: Theme;
		oncomplete: (config: UserConfig, createProfile: boolean) => void;
	} = $props();

	const t = getTranslatorContext();
	const STEPS = 3;

	let step = $state(1);
	// svelte-ignore state_referenced_locally
	let theme = $state(startingTheme);
	let card = $state<HTMLElement>();

	onMount(() => card?.focus());

	function chooseLanguage(language: Language): void {
		if (language === t.language) return;
		location.replace(`?${new URLSearchParams({ language, theme })}`);
	}

	function chooseTheme(chosen: Theme): void {
		theme = chosen;
		applyTheme(chosen);
	}

	function finish(createProfile: boolean): void {
		oncomplete({ theme, language: t.language }, createProfile);
	}
</script>

<div class="welcome__backdrop"></div>
<div class="welcome" role="dialog" aria-modal="true" aria-label={t.t('Welcome to rentczecher')} tabindex="-1" bind:this={card}>
	<div class="welcome__steps" role="img" aria-label={t.t('Step {n} of {count}', { n: step, count: STEPS })}>
		{#each { length: STEPS }, index}
			<span class="welcome__step" class:welcome__step--done={index < step}></span>
		{/each}
	</div>

	{#if step === 1}
		<img class="welcome__logo" src={logo} alt="" />
		<h2>{t.t('Welcome to rentczecher')}</h2>
		<p class="welcome__lead">{t.t('It watches the real-estate portals and shows you every new flat just once.')}</p>
		<p class="welcome__question">{t.t('Which language should the app speak?')}</p>
		<div class="welcome__choices">
			{#each LANGUAGES as language (language)}
				<button
					type="button"
					class="welcome__choice"
					class:welcome__choice--on={language === t.language}
					aria-pressed={language === t.language}
					onclick={() => chooseLanguage(language)}
				>
					<span class="welcome__flag"><Flag {language} /></span>
					<b>{LANGUAGE_NAMES[language]}</b>
				</button>
			{/each}
		</div>
	{:else if step === 2}
		<h2>{t.t('Appearance')}</h2>
		<p class="welcome__lead">{t.t('Light, dark, or following the system. Change it anytime in the top bar.')}</p>
		<div class="welcome__choices">
			{#each THEMES as option (option)}
				<button
					type="button"
					class="welcome__choice"
					class:welcome__choice--on={option === theme}
					aria-pressed={option === theme}
					onclick={() => chooseTheme(option)}
				>
					<span class="welcome__preview welcome__preview--{option}" aria-hidden="true">
						<i class="welcome__preview-bar"></i>
						<i class="welcome__preview-row"></i>
						<i class="welcome__preview-row welcome__preview-row--short"></i>
					</span>
					<b><ThemeIcon theme={option} /> {themeName(option, t)}</b>
				</button>
			{/each}
		</div>
	{:else}
		<h2>{t.t('Your first profile')}</h2>
		<p class="welcome__lead">
			{t.t(
				'A profile is a search you set up once. The app runs it again and again, keeps every flat it finds, and tells you what is new and what has changed.'
			)}
		</p>
		<ProfileShowcase />
	{/if}

	<footer class="welcome__foot">
		{#if step > 1}
			<button type="button" class="welcome__back" onclick={() => (step -= 1)}>← {t.t('Back')}</button>
		{/if}
		<span class="welcome__spacer"></span>
		{#if step < STEPS}
			<button type="button" class="welcome__primary" onclick={() => (step += 1)}>{t.t('Continue')}</button>
		{:else}
			<button type="button" class="welcome__secondary" onclick={() => finish(false)}>{t.t('Later')}</button>
			<button type="button" class="welcome__primary" onclick={() => finish(true)}>{t.t('Create profile')}</button>
		{/if}
	</footer>
</div>

<style>
	.welcome__backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		background: rgb(0 0 0 / 35%);
		backdrop-filter: blur(3px);
	}

	.welcome {
		position: fixed;
		top: 50%;
		left: 50%;
		z-index: 41;
		display: flex;
		flex-direction: column;
		width: min(42rem, 92vw);
		min-height: 26rem;
		max-height: 92vh;
		overflow-y: auto;
		padding: var(--space-6) 2rem;
		box-sizing: border-box;
		border: 1px solid var(--color-line);
		border-radius: 1rem;
		background: var(--color-card);
		color: var(--color-ink);
		box-shadow: 0 24px 64px rgb(0 0 0 / 30%);
		transform: translate(-50%, -50%);
	}

	/* The card takes focus to bring the keyboard into it, without a ring
	around all of it. */
	.welcome:focus {
		outline: none;
	}

	.welcome h2 {
		margin: var(--space-2) 0;
		font-size: 1.375rem;
	}

	.welcome__steps {
		display: flex;
		gap: var(--space-1);
	}

	.welcome__step {
		width: 1.75rem;
		height: 0.25rem;
		border-radius: var(--radius-full);
		background: var(--color-line);
	}

	.welcome__step--done {
		background: var(--color-amber);
	}

	.welcome__logo {
		width: 2.5rem;
		margin-top: var(--space-4);
	}

	.welcome__lead {
		margin: 0 0 var(--space-4);
		line-height: 1.45;
	}

	.welcome__question {
		margin: 0 0 var(--space-3);
		font-weight: 600;
	}

	/* One equal column per choice. */
	.welcome__choices {
		display: grid;
		grid-auto-columns: 1fr;
		grid-auto-flow: column;
		gap: var(--space-3);
	}

	.welcome__choice {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-3);
		border: 1px solid var(--color-line);
		border-radius: var(--radius-md);
		background: var(--color-ground);
		color: var(--color-ink);
		font-size: 0.9375rem;
		cursor: pointer;
	}

	.welcome__choice--on {
		border-color: var(--color-amber);
		box-shadow: 0 0 0 1px var(--color-amber);
	}

	.welcome__flag {
		height: 2.25rem;
	}

	/* A sketch of the app in each theme, drawn in that theme's own colours
	whatever the app shows now. */
	.welcome__preview {
		display: flex;
		flex-direction: column;
		gap: 4px;
		width: 100%;
		height: 4rem;
		padding: 6px;
		box-sizing: border-box;
		border: 1px solid var(--color-line);
		border-radius: var(--radius-sm);
	}

	.welcome__preview--light {
		background: #faf5ec;
	}

	.welcome__preview--dark {
		background: #343330;
	}

	.welcome__preview--system {
		background: linear-gradient(135deg, #faf5ec 50%, #343330 50%);
	}

	.welcome__preview-bar {
		width: 40%;
		height: 8px;
		border-radius: 2px;
		background: #dc851f;
	}

	.welcome__preview-row {
		height: 8px;
		border-radius: 2px;
		background: color-mix(in srgb, #8a8676 60%, transparent);
	}

	.welcome__preview-row--short {
		width: 60%;
	}

	.welcome__foot {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin-top: auto;
		padding-top: var(--space-6);
	}

	.welcome__spacer {
		flex: 1;
	}

	.welcome__primary,
	.welcome__secondary {
		padding: var(--space-2) var(--space-4);
		border-radius: var(--radius-full);
		font-weight: 600;
		cursor: pointer;
	}

	.welcome__primary {
		border: none;
		background: var(--color-amber);
		color: var(--color-on-amber);
	}

	.welcome__secondary {
		border: 1px solid var(--color-line);
		background: none;
		color: var(--color-ink);
	}

	.welcome__back {
		border: none;
		background: none;
		color: var(--color-bronze);
		cursor: pointer;
	}
</style>
