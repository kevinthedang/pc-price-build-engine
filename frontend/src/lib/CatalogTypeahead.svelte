<script lang="ts">
	interface CatalogItem {
		id: string;
		name: string;
	}

	interface Props {
		id: string;
		label: string;
		placeholder: string;
		items: CatalogItem[];
		onSelect: (item: CatalogItem) => void;
		onQuery: () => void;
	}

	let { id, label, placeholder, items, onSelect, onQuery }: Props = $props();
	let query = $state('');
	let isOpen = $state(false);
	let activeIndex = $state(0);
	let matchingItems = $derived.by(() => {
		const search = query.trim().toLocaleLowerCase();
		return search ? items.filter((item) => item.name.toLocaleLowerCase().includes(search)) : [];
	});

	function updateQuery(value: string) {
		query = value;
		isOpen = Boolean(value.trim());
		activeIndex = -1;
		onQuery();
	}

	function selectItem(item: CatalogItem) {
		query = item.name;
		isOpen = false;
		onSelect(item);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowDown' && matchingItems.length > 0) {
			event.preventDefault();
			isOpen = true;
			activeIndex = (activeIndex + 1) % matchingItems.length;
		} else if (event.key === 'ArrowUp' && matchingItems.length > 0) {
			event.preventDefault();
			isOpen = true;
			activeIndex =
				activeIndex < 0
					? matchingItems.length - 1
					: (activeIndex - 1 + matchingItems.length) % matchingItems.length;
		} else if (event.key === 'Enter' && isOpen && matchingItems.length > 0) {
			event.preventDefault();
			selectItem(matchingItems[Math.max(activeIndex, 0)]);
		} else if (event.key === 'Escape') {
			isOpen = false;
		}
	}
</script>

<label class="typeahead-field" for={id}>
	{label}:
	<div class="typeahead">
		<input
			type="text"
			{id}
			role="combobox"
			aria-autocomplete="list"
			aria-haspopup="listbox"
			aria-expanded={isOpen && matchingItems.length > 0}
			aria-controls="{id}-suggestions"
			aria-activedescendant={isOpen && matchingItems[activeIndex]
				? `${id}-option-${matchingItems[activeIndex].id}`
				: undefined}
			autocomplete="off"
			{placeholder}
			value={query}
			oninput={(event) => updateQuery(event.currentTarget.value)}
			onkeydown={handleKeydown}
			onblur={() => (isOpen = false)}
			required
		/>
		{#if isOpen && query.trim()}
			{#if matchingItems.length > 0}
				<ul
					class="suggestions"
					id="{id}-suggestions"
					role="listbox"
					aria-label="{label} suggestions"
				>
					{#each matchingItems as item, index (item.id)}
						<li
							id="{id}-option-{item.id}"
							role="option"
							aria-selected={index === activeIndex}
							tabindex="-1"
							onmousedown={(event) => event.preventDefault()}
							onclick={() => selectItem(item)}
							onkeydown={(event) => {
								if (event.key === 'Enter' || event.key === ' ') {
									event.preventDefault();
									selectItem(item);
								}
							}}
						>
							{item.name}
						</li>
					{/each}
				</ul>
			{:else}
				<p class="no-results" role="status">No matching {label.toLowerCase()}s found.</p>
			{/if}
		{/if}
	</div>
</label>

<style>
	.typeahead-field {
		display: grid;
		gap: 0.5rem;
		margin-block: 1rem;
	}

	.typeahead {
		position: relative;
	}

	.typeahead input {
		box-sizing: border-box;
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #aaa;
		border-radius: 0.375rem;
		font: inherit;
	}

	.suggestions,
	.no-results {
		position: absolute;
		z-index: 1;
		top: 100%;
		right: 0;
		left: 0;
		margin: 0;
		border: 1px solid #aaa;
		border-radius: 0.375rem;
		background: #fff;
		box-shadow: 0 0.25rem 0.75rem rgb(0 0 0 / 12%);
	}

	.suggestions {
		max-height: 16rem;
		overflow-y: auto;
		padding: 0.25rem;
		list-style: none;
	}

	.suggestions li {
		padding: 0.625rem 0.75rem;
		border-radius: 0.25rem;
		cursor: pointer;
	}

	.suggestions li[aria-selected='true'],
	.suggestions li:hover {
		background: #f0f4f8;
	}

	.no-results {
		padding: 0.75rem;
		color: #555;
	}
</style>
