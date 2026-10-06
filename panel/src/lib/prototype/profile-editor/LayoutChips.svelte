<!-- PROTOTYPE, throwaway. Layout codes as chips, grouped by room count. In
set mode a click toggles a layout. In ranked mode the picked ones line up in
order and can be moved. -->
<script lang="ts">
	let {
		selected = $bindable(),
		options,
		ranked = false
	}: { selected: string[]; options: readonly string[]; ranked?: boolean } = $props();

	const groups = $derived.by(() => {
		const byRooms = new Map<string, string[]>();
		for (const code of options) {
			const key = code === 'atypicky' ? 'other' : code.split('+')[0];
			byRooms.set(key, [...(byRooms.get(key) ?? []), code]);
		}
		return [...byRooms.entries()];
	});

	function toggle(code: string): void {
		selected = selected.includes(code) ? selected.filter((c) => c !== code) : [...selected, code];
	}

	function move(index: number, by: number): void {
		const next = [...selected];
		const [item] = next.splice(index, 1);
		next.splice(index + by, 0, item);
		selected = next;
	}

	const label = (code: string) => (code === 'atypicky' ? 'atypical' : code);
	const ORDINAL = ['1st', '2nd', '3rd'];
</script>

<div class="chips">
	{#each groups as [rooms, codes] (rooms)}
		<span class="group">
			{#each codes as code (code)}
				<button type="button" class="chip" class:on={selected.includes(code)} aria-pressed={selected.includes(code)} onclick={() => toggle(code)}>{label(code)}</button>
			{/each}
		</span>
	{/each}
</div>

{#if ranked && selected.length > 0}
	<ol class="ranking">
		{#each selected as code, i (code)}
			<li>
				<span class="rank">{ORDINAL[i] ?? `${i + 1}th`}</span>
				<span class="name">{label(code)}</span>
				<button type="button" disabled={i === 0} aria-label="Move up" onclick={() => move(i, -1)}>↑</button>
				<button type="button" disabled={i === selected.length - 1} aria-label="Move down" onclick={() => move(i, 1)}>↓</button>
				<button type="button" aria-label="Remove" onclick={() => toggle(code)}>×</button>
			</li>
		{/each}
	</ol>
{/if}

<style>
	.chips { display: flex; flex-wrap: wrap; gap: var(--space-2); }
	.group { display: inline-flex; gap: 2px; }
	.chip { border: 1px solid var(--color-line); background: var(--color-card); color: inherit; padding: var(--space-1) var(--space-2); cursor: pointer; font-size: 0.8125rem; min-width: 2.75rem; }
	.group .chip:first-child { border-radius: var(--radius-full) 0 0 var(--radius-full); }
	.group .chip:last-child { border-radius: 0 var(--radius-full) var(--radius-full) 0; }
	.group .chip:only-child { border-radius: var(--radius-full); }
	.chip.on { background: var(--color-olive); border-color: var(--color-olive); color: var(--color-ground); }
	.ranking { list-style: none; padding: 0; margin: var(--space-3) 0 0; display: flex; flex-direction: column; gap: var(--space-1); }
	.ranking li { display: grid; grid-template-columns: 2.5rem 1fr auto auto auto; align-items: center; gap: var(--space-1); background: var(--color-card); border: 1px solid var(--color-line); border-radius: var(--radius-md); padding: var(--space-1) var(--space-2); font-size: 0.875rem; }
	.rank { color: var(--color-bronze); font-size: 0.75rem; font-weight: 700; }
	.ranking button { background: none; border: none; color: var(--color-bronze); cursor: pointer; padding: 0 var(--space-1); }
	.ranking button:disabled { opacity: 0.3; cursor: default; }
</style>
