<script lang="ts">
	import { onMount } from 'svelte';

	type ApiStatus = 'unknown' | 'checking' | 'online' | 'offline';
	type PricingMode = 'cheapest' | 'budget' | 'balanced' | 'premium' | 'top_of_line';
	type CurrencyCode = 'USD' | 'CAD' | 'EUR' | 'GBP' | 'AUD' | 'JPY';
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
			cost_breakdown_cents: Record<string, number>;
			budget_status: string;
			mode: PricingMode;
		};
		selected_parts: Record<string, CatalogItem | null>;
		report: string;
	}

	interface ExchangeRateResponse {
		amount: number;
		base: string;
		date: string;
		rates: Partial<Record<CurrencyCode, number>>;
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
	let selectedBudget = $state<string | number>('');
	let selectedCurrency = $state<CurrencyCode>('USD');
	let exchangeRates = $state<Partial<Record<CurrencyCode, number>>>({ USD: 1 });
	let exchangeRateDate = $state('');
	let exchangeRateError = $state('');
	let buildResult = $state<BuildResult | null>(null);
	const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? '';
	const supportedCurrencies: { code: CurrencyCode; name: string }[] = [
		{ code: 'USD', name: 'US Dollar' },
		{ code: 'CAD', name: 'Canadian Dollar' },
		{ code: 'EUR', name: 'Euro' },
		{ code: 'GBP', name: 'British Pound' },
		{ code: 'AUD', name: 'Australian Dollar' },
		{ code: 'JPY', name: 'Japanese Yen' }
	];
	let selectedExchangeRate = $derived(exchangeRates[selectedCurrency]);

	function formatAmount(amount: number, currency: CurrencyCode): string {
		return new Intl.NumberFormat(undefined, {
			style: 'currency',
			currency,
			maximumFractionDigits: currency === 'JPY' ? 0 : 2
		}).format(amount);
	}

	function formatCurrency(cents: number, currency: CurrencyCode): string {
		const rate = exchangeRates[currency];
		if (rate === undefined) return 'Unavailable';
		return formatAmount((cents / 100) * rate, currency);
	}
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
		return displayName === memory.name ? `${memory.name} — ${totalCapacityLabel}` : displayName;
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

	async function loadExchangeRates() {
		exchangeRateError = '';
		try {
			const response = await fetch(
				'https://api.frankfurter.dev/v1/latest?base=USD&symbols=CAD,EUR,GBP,AUD,JPY'
			);
			if (!response.ok) {
				throw new Error(`Exchange-rate service returned HTTP ${response.status}.`);
			}
			const result = (await response.json()) as ExchangeRateResponse;
			if (result.base !== 'USD' || !result.date) {
				throw new Error('Exchange-rate response is missing its USD base or rate date.');
			}
			const validatedRates: Partial<Record<CurrencyCode, number>> = { USD: 1 };
			for (const { code } of supportedCurrencies) {
				if (code === 'USD') continue;
				const rate = result.rates[code];
				if (typeof rate !== 'number' || !Number.isFinite(rate) || rate <= 0) {
					throw new Error(`A valid ${code} exchange rate was not returned.`);
				}
				validatedRates[code] = rate;
			}
			exchangeRates = validatedRates;
			exchangeRateDate = result.date;
		} catch (error) {
			exchangeRateError =
				error instanceof Error ? error.message : 'Exchange rates could not be loaded.';
			exchangeRates = { USD: 1 };
			exchangeRateDate = '';
		}
	}

	async function generateBuild(event: SubmitEvent) {
		event.preventDefault();
		buildError = '';
		buildResult = null;
		isGenerating = true;
		try {
			const budget = String(selectedBudget).trim();
			const budgetInSelectedCurrency = budget === '' ? undefined : Number(budget);
			if (
				budgetInSelectedCurrency !== undefined &&
				(!Number.isFinite(budgetInSelectedCurrency) || budgetInSelectedCurrency < 0)
			) {
				throw new Error('Enter a valid, non-negative budget.');
			}
			let budgetCents: number | undefined;
			if (budgetInSelectedCurrency !== undefined) {
				const exchangeRate = selectedExchangeRate;
				if (exchangeRate === undefined) {
					throw new Error(`A current ${selectedCurrency} exchange rate is not available.`);
				}
				budgetCents = Math.round((budgetInSelectedCurrency / exchangeRate) * 100);
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
		void loadExchangeRates();
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
	<aside class="disclaimer" aria-label="Development disclaimer">
		<strong>Experimental — under active development.</strong>
		Compatibility checks and price estimates may be incomplete or inaccurate. Verify component compatibility
		and current prices before purchasing.
	</aside>

	{#if catalogError}
		<p class="error" role="alert">Unable to load component catalogs: {catalogError}</p>
	{/if}

	<form onsubmit={generateBuild}>
		<section class="form-section" aria-labelledby="components-heading">
			<h2 id="components-heading">Components</h2>
			<div class="form-grid">
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
								{memoryDisplayName(option.item)}{option.compatible === false
									? ` — ${option.reasons.join(' ')}`
									: ''}
							</option>
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
			</div>
		</section>

		{#if selectedMemory && memoryOptions.find((option) => option.item.id === selectedMemory)?.compatible === false}
			<p class="warning" role="status">
				The selected memory kit is not compatible with the CPU and form factor. Choose a compatible
				kit or enable “show incompatible options” to review the reason.
			</p>
		{/if}

		<section class="form-section" aria-labelledby="preferences-heading">
			<h2 id="preferences-heading">Build preferences</h2>
			<div class="form-grid">
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
					Budget limit ({selectedCurrency}, optional):
					<input
						type="number"
						id="budget"
						min="0"
						step={selectedCurrency === 'JPY' ? 1 : 0.01}
						bind:value={selectedBudget}
						placeholder={selectedCurrency === 'JPY' ? '150000' : '1500.00'}
					/>
				</label>

				<label for="currency">
					Display currency:
					<select id="currency" bind:value={selectedCurrency}>
						{#each supportedCurrencies as currency (currency.code)}
							<option value={currency.code} disabled={exchangeRates[currency.code] === undefined}>
								{currency.code} — {currency.name}
							</option>
						{/each}
					</select>
				</label>
			</div>

			{#if selectedCurrency !== 'USD' && selectedExchangeRate !== undefined}
				<p class="rate-note" aria-live="polite">
					1 USD = {formatAmount(selectedExchangeRate, selectedCurrency)}
					{#if exchangeRateDate}
						· Rate date: {exchangeRateDate}{/if}
				</p>
			{/if}
			{#if exchangeRateError}
				<p class="warning" role="status">
					Exchange rates unavailable: {exchangeRateError} Prices remain available in USD.
				</p>
			{/if}
		</section>

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
				Estimated total: {formatCurrency(
					buildResult.pricing.estimated_total_cents,
					selectedCurrency
				)}
				{#if buildResult.pricing.budget_status !== 'n/a'}
					({buildResult.pricing.budget_status})
				{/if}
			</p>
			<h3>Estimated component costs ({selectedCurrency})</h3>
			<dl class="cost-breakdown">
				{#each Object.entries(buildResult.pricing.cost_breakdown_cents) as [component, cents] (component)}
					<div>
						<dt>{component}</dt>
						<dd>{formatCurrency(cents, selectedCurrency)}</dd>
					</div>
				{/each}
			</dl>
			<details>
				<summary>Detailed build report (original USD prices)</summary>
				<pre class="result">{buildResult.report}</pre>
			</details>
			<p class="disclaimer">
				Converted amounts are estimates using the exchange rate dated {exchangeRateDate || 'above'}.
				They do not include local taxes, import charges, retailer-specific pricing, or payment
				provider fees. Confirm the purchase price with the retailer.
			</p>
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

	.form-section {
		margin-block: 1.5rem;
		padding: 1.25rem;
		border: 1px solid #ddd;
		border-radius: 0.5rem;
	}

	.form-section h2 {
		margin: 0 0 1rem;
		font-size: 1.2rem;
	}

	.form-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.25rem 1.25rem;
	}

	.disclaimer {
		margin-block: 1.5rem;
		padding: 0.875rem 1rem;
		border: 1px solid #e5c778;
		border-radius: 0.375rem;
		background: #fff8e5;
		color: #624900;
		line-height: 1.5;
	}

	.disclaimer strong {
		display: block;
		margin-bottom: 0.25rem;
	}

	.builder label {
		display: grid;
		gap: 0.5rem;
		margin-block: 1rem;
	}

	.form-grid label {
		margin-block: 0.5rem;
	}

	.builder select,
	.builder button {
		box-sizing: border-box;
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #aaa;
		border-radius: 0.375rem;
		font: inherit;
	}

	.builder input:not([type='checkbox']) {
		box-sizing: border-box;
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

	.rate-note {
		margin-top: -0.5rem;
		color: #555;
		font-size: 0.9rem;
	}

	.cost-breakdown {
		display: grid;
		gap: 0.5rem;
		max-width: 24rem;
	}

	.cost-breakdown div {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
	}

	.cost-breakdown dd {
		margin: 0;
		font-variant-numeric: tabular-nums;
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

	@media (max-width: 38rem) {
		.builder {
			padding: 1rem;
		}

		.form-section {
			padding: 1rem;
		}

		.form-grid {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
