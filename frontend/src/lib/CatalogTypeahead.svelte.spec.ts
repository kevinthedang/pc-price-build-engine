import { page, userEvent } from 'vitest/browser';
import { describe, expect, it, vi } from 'vitest';
import { render } from 'vitest-browser-svelte';
import CatalogTypeahead from './CatalogTypeahead.svelte';

const cpus = [
	{ id: 'cpu-1', name: 'Ryzen 5 5500' },
	{ id: 'cpu-2', name: 'Core i5-12400F' }
];
const gpus = [
	{ id: 'gpu-1', name: 'Gigabyte GeForce RTX 4060 WINDFORCE OC 8G' },
	{ id: 'gpu-2', name: 'SAPPHIRE PULSE Radeon RX 7600 8GB' }
];

describe('CatalogTypeahead.svelte', () => {
	it('suggests catalog matches when searching by part of the name', async () => {
		const onSelect = vi.fn();
		const onQuery = vi.fn();
		render(CatalogTypeahead, {
			id: 'cpu',
			label: 'CPU',
			placeholder: 'Search CPUs',
			items: cpus,
			onSelect,
			onQuery
		});

		const input = page.getByRole('combobox', { name: 'CPU:' });
		await input.fill('i5');

		const match = page.getByRole('option', { name: 'Core i5-12400F' });
		await expect.element(match).toBeInTheDocument();
		await match.click();

		expect(onQuery).toHaveBeenCalled();
		expect(onSelect).toHaveBeenCalledWith(cpus[1]);
		await expect.element(input).toHaveValue('Core i5-12400F');
	});

	it('selects the active suggestion with the keyboard', async () => {
		const onSelect = vi.fn();
		render(CatalogTypeahead, {
			id: 'cpu',
			label: 'CPU',
			placeholder: 'Search CPUs',
			items: cpus,
			onSelect,
			onQuery: vi.fn()
		});

		const input = page.getByRole('combobox', { name: 'CPU:' });
		await input.fill('5500');
		await userEvent.keyboard('{Enter}');

		expect(onSelect).toHaveBeenCalledWith(cpus[0]);
		await expect.element(input).toHaveValue('Ryzen 5 5500');
	});

	it('finds both RTX and RX graphics cards', async () => {
		render(CatalogTypeahead, {
			id: 'gpu',
			label: 'GPU',
			placeholder: 'Search GPUs',
			items: gpus,
			onSelect: vi.fn(),
			onQuery: vi.fn()
		});

		const input = page.getByRole('combobox', { name: 'GPU:' });
		await input.fill('RTX');
		await expect
			.element(page.getByRole('option', { name: 'Gigabyte GeForce RTX 4060 WINDFORCE OC 8G' }))
			.toBeInTheDocument();

		await input.fill('RX');
		await expect
			.element(page.getByRole('option', { name: 'SAPPHIRE PULSE Radeon RX 7600 8GB' }))
			.toBeInTheDocument();
	});
});
