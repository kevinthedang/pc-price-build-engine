<script lang="ts">
	import { onMount } from 'svelte';

	type ApiStatus = 'unknown' | 'checking' | 'online' | 'offline';
	type PricingMode = 'cheapest' | 'budget' | 'balanced' | 'premium' | 'top_of_line';
	type CatalogName =
		'cpus' | 'gpus' | 'storage' | 'memory' | 'motherboards' | 'cases' | 'coolers' | 'psus';

	interface CatalogItem {
		id: string;
		name: string;
		form_factor?: string;
	}

	interface BuildResult {
		compatible: boolean;
		pricing: {
			estimated_total_cents: number;
			budget_status: string;
			mode: PricingMode;
		};
		report: string;
	}

	const catalogNames: CatalogName[] = [
		'cpus',
		'gpus',
		'storage',
		'memory',
		'motherboards',
		'cases',
		'coolers',
		'psus'
	];

	let apiStatus = $state<ApiStatus>('unknown');
	let catalogError = $state('');
	let buildError = $state('');
	let isGenerating = $state(false);
	let cpus = $state<CatalogItem[]>([]);
	let gpus = $state<CatalogItem[]>([]);
	let storages = $state<CatalogItem[]>([]);
	let memoryKits = $state<CatalogItem[]>([]);
	let motherboards = $state<CatalogItem[]>([]);
	let selectedCpu = $state('');
	let selectedGpu = $state('');
	let selectedStorage = $state('');
	let selectedMemory = $state('');
	let selectedFormFactor = $state('');
	let selectedMode = $state<PricingMode>('budget');
	let selectedBudget = $state('');
	let buildResult = $state<BuildResult | null>(null);
	const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? '';
	let formFactors = $derived(
		[...new Set(motherboards.map((motherboard) => motherboard.form_factor).filter(Boolean))].sort()
	);

	async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
		const response = await fetch(`${apiBaseUrl}${url}`, init);
		if (!response.ok) {
			const body: { detail?: unknown } = await response.json();
			const message =
				typeof body.detail === 'string'
					? body.detail
					: JSON.stringify(body.detail ?? `Request failed (${response.status})`);
			throw new Error(message);
		}
		return response.json() as Promise<T>;
	}

	async function loadCatalogs() {
		try {
			const catalogs = await Promise.all(
				catalogNames.map((name) => fetchJson<CatalogItem[]>(`/api/catalogs/${name}`))
			);
			[cpus, gpus, storages, memoryKits, motherboards] = catalogs;
			apiStatus = 'online';
		} catch (error) {
			catalogError = error instanceof Error ? error.message : 'Could not load component catalogs.';
			apiStatus = 'offline';
		}
	}

	async function checkApiHealth() {
		try {
			const result = await fetchJson<{ status?: string }>('/api/health');
			apiStatus = result.status === 'ok' ? 'online' : 'offline';
		} catch {
			apiStatus = 'offline';
		}
	}

	async function generateBuild(event: SubmitEvent) {
		event.preventDefault();
		buildError = '';
		buildResult = null;
		isGenerating = true;
		try {
			const budget = selectedBudget.trim();
			const budgetCents = budget === '' ? undefined : Math.round(Number(budget) * 100);
			if (budgetCents !== undefined && (!Number.isFinite(budgetCents) || budgetCents < 0)) {
				throw new Error('Enter a valid, non-negative budget.');
			}
			const result = await fetchJson<BuildResult>('/api/builds/generate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					cpu_id: selectedCpu,
					gpu_id: selectedGpu,
					storage_id: selectedStorage,
					memory_id: selectedMemory,
					form_factor: selectedFormFactor || null,
					mode: selectedMode,
					...(budgetCents === undefined ? {} : { budget_limit_cents: budgetCents })
				})
			});
			buildResult = result;
		} catch (error) {
			buildError = error instanceof Error ? error.message : 'Could not generate the build.';
		} finally {
			isGenerating = false;
		}
	}

	onMount(() => {
		void loadCatalogs();
		void checkApiHealth();
	});
</script>

<svelte:head>
	<title>PC Building Optimizer</title>
	<meta
		name="description"
		content="Choose PC components and generate a compatible build using the PC Building Optimizer API."
	/>
</svelte:head>

<header class="page-header">
	<div class="health-control">
		<span class="health-dot {apiStatus}" aria-hidden="true"></span>
		<span aria-live="polite">
			{apiStatus === 'online' ? 'Online' : apiStatus === 'offline' ? 'Offline' : 'Connecting...'}
		</span>
	</div>
</header>

<main class="builder">
	<h1>PC Building Optimizer</h1>
	<p>Choose your core components to generate a compatible build.</p>

	{#if catalogError}
		<p class="error" role="alert">Unable to load component catalogs: {catalogError}</p>
	{/if}

	<form onsubmit={generateBuild}>
		<label for="cpu">
			CPU:
			<select name="cpu" id="cpu" bind:value={selectedCpu} required>
				<option value="">Choose a CPU</option>
				{#each cpus as cpu (cpu.id)}
					<option value={cpu.id}>{cpu.name}</option>
				{/each}
			</select>
		</label>

		<label for="gpu">
			GPU:
			<select name="gpu" id="gpu" bind:value={selectedGpu} required>
				<option value="">Choose a GPU</option>
				{#each gpus as gpu (gpu.id)}
					<option value={gpu.id}>{gpu.name}</option>
				{/each}
			</select>
		</label>

		<label for="storage">
			Storage:
			<select name="storage" id="storage" bind:value={selectedStorage} required>
				<option value="">Choose storage</option>
				{#each storages as storage (storage.id)}
					<option value={storage.id}>{storage.name}</option>
				{/each}
			</select>
		</label>

		<label for="memory">
			Memory:
			<select name="memory" id="memory" bind:value={selectedMemory} required>
				<option value="">Choose a memory kit</option>
				{#each memoryKits as memory (memory.id)}
					<option value={memory.id}>{memory.name}</option>
				{/each}
			</select>
		</label>

		<label for="form-factor">
			Motherboard form factor:
			<select name="form-factor" id="form-factor" bind:value={selectedFormFactor}>
				<option value="">Any form factor</option>
				{#each formFactors as formFactor (formFactor)}
					<option value={formFactor}>{formFactor}</option>
				{/each}
			</select>
		</label>

		<label for="mode">
			Pricing mode:
			<select name="mode" id="mode" bind:value={selectedMode}>
				<option value="cheapest">Cheapest</option>
				<option value="budget">Budget</option>
				<option value="balanced">Balanced</option>
				<option value="premium">Premium</option>
				<option value="top_of_line">Top of line</option>
			</select>
		</label>

		<label for="budget">
			Budget limit (USD, optional):
			<input
				type="number"
				id="budget"
				min="0"
				step="0.01"
				bind:value={selectedBudget}
				placeholder="1500.00"
			/>
		</label>

		<button type="submit" disabled={isGenerating || !!catalogError}>
			{isGenerating ? 'Generating...' : 'Generate build'}
		</button>
	</form>

	{#if buildError}
		<p class="error" role="alert">{buildError}</p>
	{/if}

	{#if buildResult}
		<section aria-live="polite">
			<h2>Generated build</h2>
			<p>
				Compatibility: {buildResult.compatible
					? 'Pass'
					: 'Some required compatibility checks failed'}
			</p>
			<p>
				Estimated total: ${(buildResult.pricing.estimated_total_cents / 100).toFixed(2)} USD
				{#if buildResult.pricing.budget_status !== 'n/a'}
					({buildResult.pricing.budget_status})
				{/if}
			</p>
			<pre class="result">{buildResult.report}</pre>
		</section>
	{/if}
</main>

<style>
	.page-header {
		display: flex;
		justify-content: flex-end;
		padding: 1rem 1.5rem;
	}

	.health-control {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.health-dot {
		display: inline-block;
		width: 0.625rem;
		height: 0.625rem;
		border-radius: 50%;
		background: #777;
	}

	.health-dot.online {
		background: #178344;
	}

	.health-dot.checking {
		background: #b87500;
	}

	.health-dot.offline {
		background: #b42318;
	}

	.builder {
		max-width: 48rem;
		margin: 0 auto;
		padding: 2rem;
	}

	.builder label {
		display: grid;
		gap: 0.5rem;
		margin-block: 1rem;
	}

	.builder select,
	.builder input,
	.builder button {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #aaa;
		border-radius: 0.375rem;
		font: inherit;
	}

	.builder button {
		margin-block: 1rem;
		cursor: pointer;
	}

	.result {
		overflow-x: auto;
		padding: 1rem;
		background: #f5f5f5;
		border-radius: 0.375rem;
		white-space: pre-wrap;
	}

	.error {
		color: #b42318;
	}
</style>
