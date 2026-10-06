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

	interface MemoryCatalogItem extends CatalogItem {
		capacity_gb: number;
		modules: number;
	}

	interface BuildResult {
		compatible: boolean;
		compatibility_checks: CompatibilityCheck[];
		pricing: {
			estimated_total_cents: number;
			budget_status: string;
			mode: PricingMode;
		};
		report: string;
	}

	interface CompatibilityCheck {
		code: string;
		components: string[];
		status: 'pass' | 'fail' | 'blocked' | 'unknown';
		message: string;
	}

	interface CompatibilityOption<T> {
		item: T;
		compatible: boolean | null;
		reasons: string[];
	}

	interface FormFactorOption {
		value: string;
		compatible: boolean | null;
		reasons: string[];
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
	let memoryOptions = $state<CompatibilityOption<MemoryCatalogItem>[]>([]);
	let formFactorOptions = $state<FormFactorOption[]>([]);
	let selectedCpu = $state('');
	let selectedGpu = $state('');
	let selectedStorage = $state('');
	let selectedMemory = $state('');
	let selectedFormFactor = $state('');
	let selectedMode = $state<PricingMode>('budget');
	let selectedBudget = $state('');
	let buildResult = $state<BuildResult | null>(null);
	const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? '';
	let showIncompatibleOptions = $state(false);
	let compatibilityOptionsError = $state('');
	let optionsRequestId = 0;
	let visibleMemoryOptions = $derived(
		memoryOptions.filter(
			(option) =>
				option.compatible !== false || showIncompatibleOptions || option.item.id === selectedMemory
		)
	);
	let visibleFormFactors = $derived(
		formFactorOptions.filter(
			(option) =>
				option.compatible !== false ||
				showIncompatibleOptions ||
				option.value === selectedFormFactor
		)
	);

	function memoryDisplayName(memory: MemoryCatalogItem): string {
		const totalCapacity = memory.capacity_gb * memory.modules;
		const totalCapacityLabel = `${totalCapacity}GB total`;
		const displayName = memory.name.replace(/\b\d+\s*GB\b/i, totalCapacityLabel);
		return displayName === memory.name
			? `${memory.name} — ${totalCapacityLabel}`
			: displayName;
	}

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
			[cpus, gpus, storages] = catalogs;
			apiStatus = 'online';
			await updateBuildOptions();
		} catch (error) {
			catalogError = error instanceof Error ? error.message : 'Could not load component catalogs.';
			apiStatus = 'offline';
		}
	}

	async function updateBuildOptions() {
		const requestId = ++optionsRequestId;
		compatibilityOptionsError = '';
		const query = new URLSearchParams();
		if (selectedCpu) query.set('cpu_id', selectedCpu);
		if (selectedFormFactor) query.set('form_factor', selectedFormFactor);
		if (selectedMemory) query.set('memory_id', selectedMemory);
		try {
			const options = await fetchJson<{
				memory: CompatibilityOption<MemoryCatalogItem>[];
				form_factors: FormFactorOption[];
			}>(`/api/builds/options?${query.toString()}`);
			if (requestId !== optionsRequestId) return;
			memoryOptions = options.memory;
			formFactorOptions = options.form_factors;
		} catch (error) {
			if (requestId !== optionsRequestId) return;
			compatibilityOptionsError =
				error instanceof Error ? error.message : 'Could not check component compatibility.';
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
			<select
				name="cpu"
				id="cpu"
				bind:value={selectedCpu}
				onchange={() => void updateBuildOptions()}
				required
			>
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
			<select
				name="memory"
				id="memory"
				bind:value={selectedMemory}
				onchange={() => void updateBuildOptions()}
				required
			>
				<option value="">Choose a memory kit</option>
				{#each visibleMemoryOptions as option (option.item.id)}
					<option value={option.item.id}>
						{memoryDisplayName(option.item)}{option.compatible === false ? ` — ${option.reasons.join(' ')}` : ''}
					</option>
				{/each}
			</select>
		</label>

		{#if selectedMemory && memoryOptions.find((option) => option.item.id === selectedMemory)?.compatible === false}
			<p class="warning" role="status">
				The selected memory kit is not compatible with the CPU and form factor. Choose a compatible
				kit or enable “show incompatible options” to review the reason.
			</p>
		{/if}

		<label for="form-factor">
			Motherboard form factor:
			<select
				name="form-factor"
				id="form-factor"
				bind:value={selectedFormFactor}
				onchange={() => void updateBuildOptions()}
			>
				<option value="">Any form factor</option>
				{#each visibleFormFactors as option (option.value)}
					<option value={option.value}>
						{option.value}{option.compatible === false ? ` — ${option.reasons.join(' ')}` : ''}
					</option>
				{/each}
			</select>
		</label>

		<label class="toggle" for="show-incompatible">
			<input type="checkbox" id="show-incompatible" bind:checked={showIncompatibleOptions} />
			Show incompatible options and why they do not fit
		</label>
		{#if compatibilityOptionsError}
			<p class="warning" role="status">
				Could not pre-filter options: {compatibilityOptionsError}. The API will still check
				compatibility when you generate a build.
			</p>
		{/if}

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
					? 'No known compatibility failures'
					: 'Some compatibility checks failed'}
			</p>
			<ul class="compatibility-checks">
				{#each buildResult.compatibility_checks as check (check.code)}
					<li class={check.status}>
						<strong>{check.status.toUpperCase()}</strong>
						<span>{check.message}</span>
					</li>
				{/each}
			</ul>
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
	.builder button {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #aaa;
		border-radius: 0.375rem;
		font: inherit;
	}

	.builder input:not([type='checkbox']) {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #aaa;
		border-radius: 0.375rem;
		font: inherit;
	}

	.builder label.toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.builder label.toggle input {
		width: auto;
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

	.warning {
		color: #805500;
	}

	.compatibility-checks {
		display: grid;
		gap: 0.5rem;
		padding-left: 1.25rem;
	}

	.compatibility-checks li {
		padding-left: 0.25rem;
	}

	.compatibility-checks .fail {
		color: #b42318;
	}

	.compatibility-checks .unknown,
	.compatibility-checks .blocked {
		color: #805500;
	}
</style>
