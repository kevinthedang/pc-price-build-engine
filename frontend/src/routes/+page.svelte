<script lang="ts">
    import { onMount } from "svelte"

    let selectedCpu = $state("")
    let selectedGpu = $state("")
    let selectedStorage = $state("")
    let selectedMemory = $state("")
    let selectedFormFactor = $state("")
    let selectedMode = $state("")
    let selectedBudget = $state("")
    let selectedCurrency = $state("USD")
    type ApiStatus = "unknown" | "checking" | "online" | "offline"
    let apiStatus = $state<ApiStatus>("unknown")
    let healthCheckInProgress = false

    async function checkApiHealth() {
        if (healthCheckInProgress) return
        healthCheckInProgress = true

        if (apiStatus === "unknown") {
            apiStatus = "checking"
        }

        try {
            const response = await fetch("/api/health")
            if (!response.ok) {
                throw new Error("Health check failed")
            }

            const result: { status?: string } = await response.json()
            apiStatus = result.status === "ok" ? "online" : "offline"
        } catch {
            apiStatus = "offline"
        } finally {
            healthCheckInProgress = false
        }
    }

    onMount(() => {
        void checkApiHealth()

        const checkWhenVisible = () => {
            if (document.visibilityState === "visible") {
                void checkApiHealth()
            }
        }

        const intervalId = window.setInterval(checkWhenVisible, 30_000)
        document.addEventListener("visibilitychange", checkWhenVisible)

        return () => {
            window.clearInterval(intervalId)
            document.removeEventListener("visibilitychange", checkWhenVisible)
        }
    })
</script>

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

<header class="page-header">
    <div class="health-control">
        <span class="health-dot {apiStatus}" aria-hidden="true"></span>
        <span aria-live="polite">
            {apiStatus === "online" ? "Online" :
                apiStatus === "offline" ? "Offline" : "Checking..."}
        </span>
    </div>
</header>

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
