<script lang="ts">
	import { onMount } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import CatalogTypeahead from '../lib/CatalogTypeahead.svelte';

	type ApiStatus = 'checking' | 'online' | 'offline';
	type PricingMode = 'cheapest' | 'budget' | 'balanced' | 'premium' | 'top_of_line';
	type CurrencyCode = 'USD' | 'CAD' | 'EUR' | 'GBP' | 'AUD' | 'JPY';
	interface CatalogItem {
		id: string;
		name: string;
		form_factor?: string;
	}

	interface CpuCatalogItem extends CatalogItem {
		socket: string;
		core_count: number;
		thread_count: number;
		performance_core_count?: number;
		efficiency_core_count?: number;
		base_clock_mhz: number;
		efficiency_core_base_clock_mhz?: number;
		max_clock_mhz: number;
		max_clock_type: 'Max boost' | 'Max turbo';
		tdp: number;
		stock_cooler_included: boolean;
	}

	interface GpuCatalogItem extends CatalogItem {
		vram: number;
		tdp: number;
		length_mm: number;
		game_clock_mhz?: number;
		boost_clock_mhz?: number;
		oc_game_clock_mhz?: number;
		oc_boost_clock_mhz?: number;
		pcie_standard?: string;
		recommended_psu_w?: number;
		pcie_slot_width?: number;
		display_outputs?: GpuDisplayOutput[];
	}

	interface GpuDisplayOutput {
		type: string;
		version?: string;
		count: number;
	}

	interface StorageCatalogItem extends CatalogItem {
		type: string;
		size_gb: number;
		pcie_compatibility: string[];
	}

	interface StorageSelection {
		type: string;
		capacityGb: string;
		storageId: string;
	}

	interface MemoryProfileOption {
		memory_type: string;
		capacity_gb: number;
		capacity_per_module_gb: number;
		module_count: number;
		speed_mhz: number;
		compatible: boolean | null;
		reasons: string[];
	}

	interface CompatibleMemoryOption {
		item: CatalogItem & {
			memory_type: string;
			capacity_gb: number;
			modules: number;
			speed_mhz: number;
		};
		compatible: boolean | null;
		reasons: string[];
		price_cents: number | null;
		retailer: string | null;
	}

	interface SelectedBuildPart {
		id: string | null;
		name: string;
	}

	interface BuildResult {
		compatible: boolean;
		compatibility_checks: CompatibilityCheck[];
		pricing: {
			estimated_total_cents: number;
			cost_breakdown_cents: Record<string, number>;
			unpriced_components: string[];
			budget_status: string;
			mode: PricingMode;
		};
		selected_parts: Record<string, SelectedBuildPart | SelectedBuildPart[] | null>;
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

	interface FormFactorOption {
		value: string;
		compatible: boolean | null;
		reasons: string[];
	}

	let apiStatus = $state<ApiStatus>('checking');
	let catalogError = $state('');
	let buildError = $state('');
	let isGenerating = $state(false);
	let cpus = $state<CpuCatalogItem[]>([]);
	let gpus = $state<GpuCatalogItem[]>([]);
	let storages = $state<StorageCatalogItem[]>([]);
	let memoryProfiles = $state<MemoryProfileOption[]>([]);
	let memoryOptions = $state<CompatibleMemoryOption[]>([]);
	let formFactorOptions = $state<FormFactorOption[]>([]);
	let selectedCpu = $state('');
	let selectedCpuDetails = $derived(cpus.find((cpu) => cpu.id === selectedCpu));
	let selectedGpu = $state('');
	let selectedGpuDetails = $derived(gpus.find((gpu) => gpu.id === selectedGpu));
	let storageSelections = $state<StorageSelection[]>([createStorageSelection()]);
	let selectedMemoryType = $state('');
	let selectedMemoryCapacityKey = $state('');
	let selectedMemorySpeed = $state('');
	let selectedMemoryKitId = $state('');
	let selectedFormFactor = $state('');
	let selectedMode = $state<PricingMode>('budget');
	let selectedBudget = $state<string | number>('');
	let selectedCurrency = $state<CurrencyCode>('USD');
	let exchangeRates = $state<Partial<Record<CurrencyCode, number>>>({ USD: 1 });
	let exchangeRateDate = $state('');
	let exchangeRateError = $state('');
	let buildResult = $state<BuildResult | null>(null);
	let canGenerateBuild = $derived(
		Boolean(selectedCpu && selectedGpu && selectedStorageIds.length && selectedMemoryKit) &&
			!isGenerating &&
			apiStatus === 'online' &&
			!catalogError
	);
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
	let selectedStorageIds = $derived(
		storageSelections.map((selection) => selection.storageId).filter(Boolean)
	);
	let storageTypes = $derived([...new Set(storages.map((storage) => storage.type))].sort());

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

	function createStorageSelection(): StorageSelection {
		return { type: '', capacityGb: '', storageId: '' };
	}

	function storageCapacities(type: string): number[] {
		return [
			...new Set(
				storages.filter((storage) => storage.type === type).map((storage) => storage.size_gb)
			)
		].sort((a, b) => a - b);
	}

	function matchingStorage(selection: StorageSelection): StorageCatalogItem[] {
		return storages.filter(
			(storage) =>
				storage.type === selection.type && String(storage.size_gb) === selection.capacityGb
		);
	}

	function storageTypeLabel(type: string): string {
		return type === 'NVMe SSD' ? 'M.2 NVMe SSD' : type;
	}

	function changeStorageType(index: number, type: string) {
		storageSelections = storageSelections.map((selection, selectionIndex) =>
			selectionIndex === index ? { type, capacityGb: '', storageId: '' } : selection
		);
	}

	function changeStorageCapacity(index: number, capacityGb: string) {
		storageSelections = storageSelections.map((selection, selectionIndex) =>
			selectionIndex === index ? { ...selection, capacityGb, storageId: '' } : selection
		);
	}

	function changeStorageDrive(index: number, storageId: string) {
		const updatedSelections = storageSelections.map((selection, selectionIndex) =>
			selectionIndex === index ? { ...selection, storageId } : selection
		);
		if (storageId && index === updatedSelections.length - 1) {
			updatedSelections.push(createStorageSelection());
		}
		storageSelections = updatedSelections;
	}

	function removeStorageSelection(index: number) {
		const updatedSelections = storageSelections.filter(
			(_, selectionIndex) => selectionIndex !== index
		);
		storageSelections =
			updatedSelections.length > 0 ? updatedSelections : [createStorageSelection()];
	}
	let showIncompatibleOptions = $state(false);
	let compatibilityOptionsError = $state('');
	let optionsRequestId = 0;
	let selectedMemoryProfile = $derived(
		memoryProfiles.find(
			(option) =>
				option.memory_type === selectedMemoryType &&
				`${option.module_count}:${option.capacity_gb}` === selectedMemoryCapacityKey &&
				String(option.speed_mhz) === selectedMemorySpeed
		)
	);
	let compatibleMemoryOptions = $derived(
		memoryOptions.filter((option) => option.compatible === true)
	);
	let selectedMemoryKit = $derived(
		compatibleMemoryOptions.find((option) => option.item.id === selectedMemoryKitId)
	);
	let hasMemoryCriteria = $derived(
		Boolean(selectedMemoryType && selectedMemoryCapacityKey && selectedMemorySpeed)
	);
	let visibleMemoryProfiles = $derived(
		memoryProfiles.filter(
			(option) =>
				option.compatible !== false ||
				showIncompatibleOptions ||
				(option.memory_type === selectedMemoryType &&
					(!selectedMemoryCapacityKey ||
						`${option.module_count}:${option.capacity_gb}` === selectedMemoryCapacityKey))
		)
	);
	let visibleMemoryTypes = $derived(
		[
			...new Set([
				...visibleMemoryProfiles.map((option) => option.memory_type),
				...(selectedMemoryType ? [selectedMemoryType] : [])
			])
		].sort()
	);
	let compatibleMemoryTypes = $derived(
		[
			...new Set(
				memoryProfiles
					.filter((profile) => profile.compatible === true)
					.map((profile) => profile.memory_type)
			)
		].sort()
	);
	let memoryTypeIsFixed = $derived(Boolean(selectedCpu && compatibleMemoryTypes.length === 1));
	let visibleMemoryCapacities = $derived(
		[
			...new Map(
				visibleMemoryProfiles
					.filter((option) => option.memory_type === selectedMemoryType)
					.map((option) => [
						`${option.module_count}:${option.capacity_gb}`,
						{
							key: `${option.module_count}:${option.capacity_gb}`,
							moduleCount: option.module_count,
							capacityGb: option.capacity_gb,
							capacityPerModuleGb: option.capacity_per_module_gb
						}
					])
			).values()
		].sort((a, b) => a.capacityGb - b.capacityGb || a.moduleCount - b.moduleCount)
	);
	let visibleMemorySpeeds = $derived(
		[
			...new Set(
				memoryProfiles
					.filter((option) => option.memory_type === selectedMemoryType)
					.map((option) => option.speed_mhz)
			)
		].sort((a, b) => a - b)
	);
	let visibleFormFactors = $derived(
		formFactorOptions.filter(
			(option) =>
				option.compatible !== false ||
				showIncompatibleOptions ||
				option.value === selectedFormFactor
		)
	);

	function changeMemoryType(memoryType: string) {
		selectedMemoryType = memoryType;
		selectedMemoryCapacityKey = '';
		selectedMemorySpeed = '';
		selectedMemoryKitId = '';
		void updateBuildOptions();
	}

	function changeMemoryCapacity() {
		selectedMemoryKitId = '';
		void updateBuildOptions();
	}

	function changeMemorySpeed() {
		selectedMemoryKitId = '';
		void updateBuildOptions();
	}

	function changeFormFactor(formFactor: string) {
		selectedFormFactor = formFactor;
		selectedMemoryKitId = '';
		void updateBuildOptions();
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
		apiStatus = 'checking';
		catalogError = '';
		try {
			const health = await fetchJson<{ status?: string }>('/api/health');
			if (health.status !== 'ok') {
				throw new Error('Backend API is not ready.');
			}
			const [cpuCatalog, gpuCatalog, storageCatalog] = await Promise.all([
				fetchJson<CpuCatalogItem[]>('/api/catalogs/cpus'),
				fetchJson<GpuCatalogItem[]>('/api/catalogs/gpus'),
				fetchJson<StorageCatalogItem[]>('/api/catalogs/storage')
			]);
			cpus = cpuCatalog;
			gpus = gpuCatalog;
			storages = storageCatalog;
			apiStatus = 'online';
			await updateBuildOptions();
		} catch {
			catalogError = 'The backend API is unavailable, so component options could not be loaded.';
			apiStatus = 'offline';
		}
	}

	async function updateBuildOptions() {
		const requestId = ++optionsRequestId;
		compatibilityOptionsError = '';
		const query = new SvelteURLSearchParams();
		if (selectedCpu) query.set('cpu_id', selectedCpu);
		if (selectedFormFactor) query.set('form_factor', selectedFormFactor);
		if (hasMemoryCriteria) {
			const [moduleCount, capacityGb] = selectedMemoryCapacityKey.split(':');
			query.set('memory_type', selectedMemoryType);
			query.set('memory_capacity_gb', capacityGb);
			query.set('memory_module_count', moduleCount);
			query.set('memory_speed_mhz', selectedMemorySpeed);
		}
		try {
			const options = await fetchJson<{
				memory: CompatibleMemoryOption[];
				memory_profiles: MemoryProfileOption[];
				form_factors: FormFactorOption[];
			}>(`/api/builds/options?${query.toString()}`);
			if (requestId !== optionsRequestId) return;
			memoryOptions = options.memory;
			memoryProfiles = options.memory_profiles;
			formFactorOptions = options.form_factors;
			if (selectedCpu && compatibleMemoryTypes.length === 1) {
				const [compatibleMemoryType] = compatibleMemoryTypes;
				if (selectedMemoryType !== compatibleMemoryType) {
					selectedMemoryType = compatibleMemoryType;
					selectedMemoryCapacityKey = '';
					selectedMemorySpeed = '';
					selectedMemoryKitId = '';
				}
			} else if (selectedMemoryType && !compatibleMemoryTypes.includes(selectedMemoryType)) {
				selectedMemoryType = '';
				selectedMemoryCapacityKey = '';
				selectedMemorySpeed = '';
				selectedMemoryKitId = '';
			}
			if (
				selectedMemoryKitId &&
				!compatibleMemoryOptions.some(
					(option) => option.item.id === selectedMemoryKitId && option.compatible === true
				)
			) {
				selectedMemoryKitId = '';
			}
		} catch (error) {
			if (requestId !== optionsRequestId) return;
			compatibilityOptionsError =
				error instanceof Error ? error.message : 'Could not check component compatibility.';
		}
	}

	function selectCpu(item: CatalogItem) {
		selectedCpu = item.id;
		selectedMemoryKitId = '';
		void updateBuildOptions();
	}

	function clearCpuSelection() {
		if (!selectedCpu) return;
		selectedCpu = '';
		selectedMemoryType = '';
		selectedMemoryCapacityKey = '';
		selectedMemorySpeed = '';
		selectedMemoryKitId = '';
		void updateBuildOptions();
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
		if (!canGenerateBuild || !selectedMemoryKit) return;
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
					storage_ids: selectedStorageIds,
					memory_id: selectedMemoryKit.item.id,
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
	<p>Choose your core components and check memory compatibility.</p>
	<aside class="disclaimer" aria-label="Development disclaimer">
		<strong>Experimental — under active development.</strong>
		Compatibility checks and price estimates may be incomplete or inaccurate. Verify component compatibility
		and current prices before purchasing.
	</aside>

	{#if catalogError}
		<div class="connection-error" role="alert">
			<strong>We couldn’t connect to the Catalog API.</strong>
			<p>{catalogError} Check that the backend is running, then try again.</p>
			<button class="retry-action" type="button" onclick={() => void loadCatalogs()}>
				Try again
			</button>
		</div>
	{/if}
	{#if apiStatus === 'checking'}
		<p role="status">Connecting to the Catalog API. Components will be enabled when it is ready.</p>
	{/if}

	<form onsubmit={generateBuild}>
		<fieldset
			class="builder-controls"
			aria-label="Build configuration"
			disabled={apiStatus !== 'online'}
		>
			<section class="form-section" aria-labelledby="components-heading">
				<h2 id="components-heading">Components</h2>
				<h3 id="main-components-heading">Main components</h3>
				<CatalogTypeahead
					id="cpu"
					label="CPU"
					placeholder="Search, e.g. i5 or 5500"
					items={cpus}
					onSelect={selectCpu}
					onQuery={clearCpuSelection}
				/>
				{#if selectedCpuDetails}
					<div class="cpu-specs" aria-label="{selectedCpuDetails.name} specifications">
						<dl class="cpu-spec-list">
							<div>
								<dt>Cores</dt>
								<dd>
									{selectedCpuDetails.core_count}
									{#if selectedCpuDetails.performance_core_count !== undefined}
										({selectedCpuDetails.performance_core_count} P-cores{#if selectedCpuDetails.efficiency_core_count !== undefined}
											, {selectedCpuDetails.efficiency_core_count} E-cores
										{/if})
									{/if}
								</dd>
							</div>
							<div>
								<dt>Threads</dt>
								<dd>{selectedCpuDetails.thread_count}</dd>
							</div>
							<div>
								<dt>
									{selectedCpuDetails.efficiency_core_base_clock_mhz !== undefined
										? 'P-core base'
										: 'Base clock'}
								</dt>
								<dd>{(selectedCpuDetails.base_clock_mhz / 1000).toFixed(1)} GHz</dd>
							</div>
							{#if selectedCpuDetails.efficiency_core_base_clock_mhz !== undefined}
								<div>
									<dt>E-core base</dt>
									<dd>
										{(selectedCpuDetails.efficiency_core_base_clock_mhz / 1000).toFixed(1)} GHz
									</dd>
								</div>
							{/if}
							<div>
								<dt>{selectedCpuDetails.max_clock_type}</dt>
								<dd>{(selectedCpuDetails.max_clock_mhz / 1000).toFixed(1)} GHz</dd>
							</div>
							<div>
								<dt>Socket</dt>
								<dd>{selectedCpuDetails.socket}</dd>
							</div>
							<div>
								<dt>TDP</dt>
								<dd>{selectedCpuDetails.tdp} W</dd>
							</div>
							<div>
								<dt>Stock cooler</dt>
								<dd>{selectedCpuDetails.stock_cooler_included ? 'Included' : 'Not included'}</dd>
							</div>
						</dl>
						<p>
							Advertised base and maximum clock speeds; actual speeds vary with workload, cooling,
							power limits, and system settings.
						</p>
					</div>
				{/if}

				<CatalogTypeahead
					id="gpu"
					label="GPU"
					placeholder="Search, e.g. RTX or RX"
					items={gpus}
					onSelect={(item) => (selectedGpu = item.id)}
					onQuery={() => (selectedGpu = '')}
				/>
				{#if selectedGpuDetails}
					<div class="gpu-specs" aria-label="{selectedGpuDetails.name} specifications">
						<dl class="gpu-spec-list">
							<div>
								<dt>VRAM</dt>
								<dd>{selectedGpuDetails.vram} GB</dd>
							</div>
							<div>
								<dt>Board power</dt>
								<dd>{selectedGpuDetails.tdp} W</dd>
							</div>
							<div>
								<dt>Length</dt>
								<dd>{selectedGpuDetails.length_mm} mm</dd>
							</div>
							{#if selectedGpuDetails.game_clock_mhz}
								<div>
									<dt>Game clock</dt>
									<dd>{(selectedGpuDetails.game_clock_mhz / 1000).toFixed(3)} GHz</dd>
								</div>
							{/if}
							{#if selectedGpuDetails.boost_clock_mhz}
								<div>
									<dt>Boost clock</dt>
									<dd>{(selectedGpuDetails.boost_clock_mhz / 1000).toFixed(3)} GHz</dd>
								</div>
							{/if}
							{#if selectedGpuDetails.oc_game_clock_mhz}
								<div>
									<dt>OC-mode game clock</dt>
									<dd>{(selectedGpuDetails.oc_game_clock_mhz / 1000).toFixed(3)} GHz</dd>
								</div>
							{/if}
							{#if selectedGpuDetails.oc_boost_clock_mhz}
								<div>
									<dt>OC-mode boost clock</dt>
									<dd>{(selectedGpuDetails.oc_boost_clock_mhz / 1000).toFixed(3)} GHz</dd>
								</div>
							{/if}
							{#if selectedGpuDetails.pcie_standard}
								<div>
									<dt>PCIe standard</dt>
									<dd>{selectedGpuDetails.pcie_standard}</dd>
								</div>
							{/if}
							{#if selectedGpuDetails.pcie_slot_width}
								<div>
									<dt>Card thickness</dt>
									<dd>{selectedGpuDetails.pcie_slot_width} slots</dd>
								</div>
							{/if}
							{#if selectedGpuDetails.recommended_psu_w}
								<div>
									<dt>Manufacturer PSU recommendation</dt>
									<dd>{selectedGpuDetails.recommended_psu_w} W minimum</dd>
								</div>
							{/if}
							{#if selectedGpuDetails.display_outputs?.length}
								<div>
									<dt>Display outputs</dt>
									<dd>
										{#each selectedGpuDetails.display_outputs as output, index (output.type + output.version)}
											{#if index > 0}<br />{/if}
											{output.count} × {output.type}{output.version ? ` ${output.version}` : ''}
										{/each}
									</dd>
								</div>
							{/if}
						</dl>
						{#if selectedGpuDetails.game_clock_mhz || selectedGpuDetails.boost_clock_mhz}
							<p>
								Advertised game and boost clocks are not guaranteed operating speeds; actual speeds
								vary with workload, cooling, power limits, and system settings.
							</p>
						{/if}
					</div>
				{/if}
			</section>

			<section class="form-section" aria-labelledby="memory-heading">
				<h2 id="memory-heading">Memory</h2>
				{#if !selectedCpu}
					<p class="field-hint">Choose a CPU to see compatible memory options.</p>
				{/if}
				<label for="memory-type">
					Memory type:
					<select
						name="memory-type"
						id="memory-type"
						value={selectedMemoryType}
						onchange={(event) => changeMemoryType((event.currentTarget as HTMLSelectElement).value)}
						disabled={!selectedCpu || memoryTypeIsFixed}
						required
					>
						<option value="">Choose DDR type</option>
						{#each visibleMemoryTypes as memoryType (memoryType)}
							<option value={memoryType}>{memoryType}</option>
						{/each}
					</select>
				</label>
				{#if memoryTypeIsFixed}
					<p class="field-hint">
						{selectedMemoryType} is the only memory type compatible with this CPU and form factor.
					</p>
				{/if}

				<label for="memory-capacity">
					Memory configuration:
					<select
						name="memory-capacity"
						id="memory-capacity"
						bind:value={selectedMemoryCapacityKey}
						onchange={changeMemoryCapacity}
						disabled={!selectedCpu || !selectedMemoryType}
						required
					>
						<option value="">Choose capacity and module count</option>
						{#each visibleMemoryCapacities as capacity (capacity.key)}
							<option value={capacity.key}>
								{capacity.moduleCount} × {capacity.capacityPerModuleGb} GB ({capacity.capacityGb}
								GB total)
							</option>
						{/each}
					</select>
				</label>

				<label for="memory-speed">
					Memory speed:
					<select
						name="memory-speed"
						id="memory-speed"
						bind:value={selectedMemorySpeed}
						onchange={changeMemorySpeed}
						disabled={!selectedCpu || !selectedMemoryType}
						required
					>
						<option value="">Choose speed</option>
						{#each visibleMemorySpeeds as speed (speed)}
							<option value={speed}>{speed} MHz</option>
						{/each}
					</select>
					<span class="rate-note">
						Speed is a preference; the current catalog does not include CPU or motherboard speed
						limits to verify it.
					</span>
				</label>
				{#if hasMemoryCriteria}
					<label for="memory-kit">
						Compatible catalog kit:
						<select
							name="memory-kit"
							id="memory-kit"
							bind:value={selectedMemoryKitId}
							disabled={!selectedCpu}
							required
						>
							<option value="">Choose a matching kit</option>
							{#each compatibleMemoryOptions as option (option.item.id)}
								<option value={option.item.id} disabled={option.price_cents === null}>
									{option.item.name} —
									{option.price_cents === null
										? 'Price unavailable'
										: formatCurrency(option.price_cents, selectedCurrency)}
								</option>
							{/each}
						</select>
					</label>
					{#if compatibleMemoryOptions.length === 0}
						<p class="warning" role="status">
							{selectedCpu
								? 'No catalog memory kits match these criteria and are compatible with the current CPU and form factor.'
								: 'Choose a CPU to find compatible catalog memory kits matching these criteria.'}
						</p>
					{:else if !compatibleMemoryOptions.some((option) => option.price_cents !== null)}
						<p class="warning" role="status">
							Matching kits are available, but none currently have a price, so they cannot be
							included in a priced build.
						</p>
					{/if}
				{/if}
			</section>

			<section class="form-section" aria-labelledby="storage-heading">
				<h2 id="storage-heading">Storage</h2>
				<p class="rate-note">
					Choose a drive type and capacity to see matching catalog drives. Motherboard storage-slot
					compatibility is not modeled yet.
				</p>
				{#each storageSelections as selection, index (index)}
					<div class="storage-row">
						<label for="storage-type-{index}">
							Drive type:
							<select
								name="storage-type-{index}"
								id="storage-type-{index}"
								bind:value={selection.type}
								onchange={(event) =>
									changeStorageType(index, (event.currentTarget as HTMLSelectElement).value)}
							>
								<option value="">Choose drive type</option>
								{#each storageTypes as type (type)}
									<option value={type}>{storageTypeLabel(type)}</option>
								{/each}
							</select>
						</label>
						<label for="storage-capacity-{index}">
							Capacity:
							<select
								name="storage-capacity-{index}"
								id="storage-capacity-{index}"
								bind:value={selection.capacityGb}
								onchange={(event) =>
									changeStorageCapacity(index, (event.currentTarget as HTMLSelectElement).value)}
								disabled={!selection.type}
							>
								<option value="">Choose capacity</option>
								{#each storageCapacities(selection.type) as capacity (capacity)}
									<option value={String(capacity)}>{capacity.toLocaleString()} GB</option>
								{/each}
							</select>
						</label>
						<label for="storage-drive-{index}">
							Matching drive:
							<select
								name="storage-drive-{index}"
								id="storage-drive-{index}"
								value={selection.storageId}
								onchange={(event) =>
									changeStorageDrive(index, (event.currentTarget as HTMLSelectElement).value)}
								disabled={!selection.type || !selection.capacityGb}
							>
								<option value="">Choose a drive</option>
								{#each matchingStorage(selection) as storage (storage.id)}
									<option value={storage.id}>{storage.name}</option>
								{/each}
							</select>
						</label>
						{#if selection.storageId}
							<button
								class="storage-remove"
								type="button"
								aria-label="Remove storage drive {index + 1}"
								title="Remove storage drive {index + 1}"
								onclick={() => removeStorageSelection(index)}
							>
								×
							</button>
						{/if}
					</div>
				{/each}
				<p class="storage-note">Unselected drive rows are left out of the build.</p>
			</section>

			{#if selectedMemoryProfile?.compatible === false}
				<p class="warning" role="status">
					The selected memory profile is not compatible with the CPU and form factor:
					{selectedMemoryProfile.reasons.join(' ')}
				</p>
			{:else if selectedMemoryProfile?.compatible === true}
				<p class="rate-note" role="status">
					This profile is compatible with at least one motherboard matching the selected CPU and
					form factor.
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
							onchange={(event) => changeFormFactor(event.currentTarget.value)}
						>
							<option value="">Any form factor</option>
							{#each visibleFormFactors as option (option.value)}
								<option value={option.value}>
									{option.value}{option.compatible === false
										? ` — ${option.reasons.join(' ')}`
										: ''}
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

			<div class="form-actions">
				<button class="compact-action" type="submit" disabled={!canGenerateBuild}>
					{isGenerating ? 'Generating...' : 'Generate build'}
				</button>
			</div>
		</fieldset>
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
			{#if buildResult.pricing.unpriced_components.length > 0}
				<p class="warning" role="status">
					Estimated total excludes: {buildResult.pricing.unpriced_components.join(', ')}. Those
					components do not have matched product prices yet.
				</p>
			{/if}
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

	.builder-controls {
		min-width: 0;
		margin: 0;
		padding: 0;
		border: 0;
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

	.form-section h3 {
		margin: 0 0 0.75rem;
		font-size: 1rem;
	}

	.cpu-specs {
		margin-block: 0.75rem 1.25rem;
		padding: 1rem;
		border: 1px solid #ddd;
		border-radius: 0.375rem;
		background: #fafafa;
	}

	.gpu-specs {
		margin-block: 0.75rem 1.25rem;
		padding: 1rem;
		border: 1px solid #ddd;
		border-radius: 0.375rem;
		background: #fafafa;
	}

	.gpu-spec-list {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: 0.75rem 1rem;
		margin: 0;
	}

	.gpu-spec-list div {
		min-width: 0;
	}

	.gpu-spec-list dt {
		color: #555;
		font-size: 0.875rem;
	}

	.gpu-spec-list dd {
		margin: 0.2rem 0 0;
		font-weight: 600;
	}

	.gpu-specs p {
		margin: 0.75rem 0 0;
		color: #555;
		font-size: 0.875rem;
	}

	.cpu-spec-list {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
		gap: 0.75rem 1rem;
		margin: 0;
	}

	.cpu-spec-list div {
		min-width: 0;
	}

	.cpu-spec-list dt {
		color: #555;
		font-size: 0.875rem;
	}

	.cpu-spec-list dd {
		margin: 0.2rem 0 0;
		font-weight: 600;
	}

	.cpu-specs p {
		margin: 0.75rem 0 0;
		color: #555;
		font-size: 0.875rem;
	}

	.field-hint {
		margin: 0 0 0.75rem;
		color: #555;
		font-size: 0.9rem;
	}

	.form-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.25rem 1.25rem;
	}

	.storage-row {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
		align-items: end;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
		padding: 0.75rem;
		border: 1px solid #ddd;
		border-radius: 0.5rem;
		background: #fafafa;
	}

	.builder button.storage-remove {
		display: grid;
		width: 2.75rem;
		height: 2.75rem;
		margin: 0;
		padding: 0;
		align-self: end;
		justify-self: end;
		grid-column: 4;
		grid-row: 1;
		place-items: center;
		border-color: #c9c9c9;
		background: #fff;
		color: #555;
		font-size: 1.75rem;
		line-height: 1;
		cursor: pointer;
	}

	.builder button.storage-remove:hover {
		border-color: #b42318;
		background: #fff4f2;
		color: #b42318;
	}

	.builder button.storage-remove:focus-visible {
		outline: 2px solid #175cd3;
		outline-offset: 2px;
	}

	.builder .storage-row label {
		grid-row: 1;
		min-width: 0;
		margin-block: 0;
	}

	.storage-note {
		margin: 0.75rem 0 0;
		color: #555;
		font-size: 0.9rem;
	}

	@media (max-width: 40rem) {
		.storage-row {
			grid-template-columns: minmax(0, 1fr);
		}

		.builder .storage-row label {
			grid-row: auto;
		}

		.builder button.storage-remove {
			grid-column: 1;
			grid-row: auto;
			justify-self: end;
		}
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

	.connection-error {
		margin-block: 1.5rem;
		padding: 1rem;
		border: 1px solid #e4a9a5;
		border-radius: 0.375rem;
		background: #fff4f2;
		color: #7a271a;
		line-height: 1.5;
	}

	.connection-error p {
		margin: 0.5rem 0 1rem;
	}

	.builder button.retry-action {
		width: auto;
		margin: 0;
		border-color: #b42318;
		background: #fff;
		color: #7a271a;
		cursor: pointer;
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

	.form-actions {
		display: flex;
		justify-content: flex-end;
		margin-top: 1.25rem;
	}

	.builder button.compact-action {
		width: auto;
		min-width: 12rem;
		margin: 0;
		cursor: pointer;
	}

	.builder button.compact-action:disabled {
		cursor: not-allowed;
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

		.form-actions,
		.builder button.compact-action {
			width: 100%;
		}

		.storage-row {
			grid-template-columns: minmax(0, 1fr);
		}

		.builder button.storage-remove {
			width: 2.75rem;
		}
	}
</style>
