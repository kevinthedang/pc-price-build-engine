<script>
    let selectedCpu = $state("")
    let selectedGpu = $state("")
    let selectedStorage = $state("")
    let selectedMemory = $state("")
    let selectedFormFactor = $state("")
    let selectedMode = $state("")
    let selectedBudget = $state("")
    let selectedCurrency = $state("USD")
</script>

<style>
    .builder {
        max-width: 44rem;
        margin: 0 auto;
        padding: 2rem;
    }

    .builder label {
        display: grid;
        gap: 0.5rem;
        margin-block: 1rem;
    }

    .builder select,
    .builder input {
        width: 100%;
        padding: 0.75rem;
        border: 1px solid #aaa;
        border-radius: 0.375rem;
        font: inherit;
    }

    .budget-controls {
        display: flex;
        gap: 0.5rem;
    }

    .budget-controls input {
        flex: 1;
        min-width: 0;
    }

    .budget-controls select {
        width: auto;
    }
</style>

<main class="builder">
    <h1>PC Building Optimizer</h1>

    <label for="cpu">
        CPU:
        <select name="cpu" id="cpu" bind:value={selectedCpu}>
            <option value="">Choose a CPU</option>
            <option value="cpu-000000002">Ryzen 5 5600</option>
        </select>
    </label>

    <label for="gpu">
        GPU:
        <select name="gpu" id="gpu" bind:value={selectedGpu}>
            <option value="">Choose a GPU</option>
            <option value="gpu-000000002">RTX 3060</option>
        </select>
    </label>

    <label for="storage">
        Storage:
        <select name="storage" id="storage2" bind:value={selectedStorage}>
            <option value="">Choose a Storage</option>
            <option value="storage-000000002">512GB SSD</option>
        </select>
    </label>

    <label for="memory">
        Memory/RAM:
        <select name="memory" id="memory" bind:value={selectedMemory}>
            <option value="">Choose a Memory/RAM</option>
            <option value="memory-000000002">16GB DDR4</option>
        </select>
    </label>

    <label for="formfactor">
        Form Factor:
        <select name="formfactor" id="formfactor" bind:value={selectedFormFactor}>
            <option value="">Choose a Form Factor</option>
            <option value="formfactor-000000002">ATX</option>
        </select>
    </label>

    <label for="mode">
        Mode:
        <select name="mode" id="mode" bind:value={selectedMode}>
            <option value="">Choose a Mode</option>
            <option value="mode-000000002">Performance</option>
        </select>
    </label>

    <label for="budget">
        Budget:
        <div class="budget-controls">
            <input type="text" id="budget" bind:value={selectedBudget}>
            <select name="currency" id="currency" bind:value={selectedCurrency}>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
            </select>
        </div>
    </label>
</main>



{#if selectedCpu}
    <p>Selected CPU: {selectedCpu}</p>
{/if}