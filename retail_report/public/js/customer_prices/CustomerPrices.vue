<template>
	<div class="cp-root">
		<div v-if="loading" class="cp-empty">
			<i class="fa fa-spinner fa-spin"></i> {{ __('Loading customer prices…') }}
		</div>

		<div v-else-if="!items.length" class="cp-empty">
			{{ __('This invoice has no items yet.') }}
		</div>

		<template v-else>
			<div class="cp-toolbar">
				<div class="cp-field">
					<label>{{ __('Item') }}</label>
					<select v-model="activeItem">
						<option v-for="it in items" :key="it.item_code" :value="it.item_code">
							{{ it.item_code }} — {{ it.item_name }}
						</option>
					</select>
				</div>
				<div v-if="activeItemDoc" class="cp-uominfo">
					<span><b>{{ activeItemDoc.unit_uom }}</b> {{ __('single') }}</span>
					<span v-if="activeItemDoc.block_uom">
						/ <b>{{ activeItemDoc.block_uom }}</b> × {{ activeItemDoc.block_factor }}
					</span>
					<span v-else class="cp-muted">/ {{ __('no block UOM') }}</span>
				</div>
				<label class="cp-check">
					<input type="checkbox" v-model="onlyWithPrice" />
					{{ __('Only customers with a price') }}
				</label>
				<label class="cp-check">
					<input type="checkbox" v-model="showBonus" />
					{{ __('Bonus') }}
				</label>
				<div class="cp-spacer"></div>
				<span v-if="dirtyCells.length" class="cp-dirty">
					{{ __('{0} unsaved', [dirtyCells.length]) }}
				</span>
			</div>

			<div class="cp-scroll">
				<table class="cp-table">
					<thead>
						<tr>
							<th class="cp-col-cust" rowspan="2">{{ __('Customer') }}</th>
							<th v-for="pl in priceLists" :key="pl.name" colspan="2" class="cp-plhead">
								<span class="cp-plname" :title="pl.name">{{ pl.name }}</span>
								<button
									class="cp-mini"
									:title="__('Fill this price list from the general price')"
									@click="fillFromGeneral(pl.name)"
								>=</button>
								<button
									class="cp-mini"
									:title="__('Apply a percentage to this price list')"
									@click="applyPercent(pl.name)"
								>%</button>
							</th>
						</tr>
						<tr>
							<template v-for="pl in priceLists">
								<th :key="pl.name + '-u'" class="cp-col-num cp-sub">{{ unitUom }}</th>
								<th :key="pl.name + '-b'" class="cp-col-num cp-sub">
									{{ blockUom || '—' }}
								</th>
							</template>
						</tr>
					</thead>
					<tbody>
						<tr class="cp-general-row">
							<td class="cp-col-cust">{{ __('General price') }}</td>
							<template v-for="pl in priceLists">
								<td :key="pl.name + '-gu'" class="cp-col-num">
									{{ fmt(generalRate(pl.name, unitUom)) }}
								</td>
								<td :key="pl.name + '-gb'" class="cp-col-num">
									{{ fmt(generalRate(pl.name, blockUom)) }}
								</td>
							</template>
						</tr>

						<tr v-for="c in visibleCustomers" :key="c.name">
							<td class="cp-col-cust" :title="c.name">{{ c.customer_name || c.name }}</td>
							<template v-for="pl in priceLists">
								<td
									v-for="uom in [unitUom, blockUom]"
									:key="pl.name + '-' + uom + '-' + c.name"
									class="cp-col-num"
								>
									<template v-if="uom">
										<input
											type="number"
											step="0.01"
											min="0"
											class="cp-input"
											:class="cellClass(pl.name, uom, c.name)"
											:title="cellTitle(pl.name, uom, c.name)"
											v-model="cell(pl.name, uom, c.name).rate"
										/>
										<input
											v-if="showBonus"
											type="number"
											step="0.01"
											min="0"
											class="cp-input cp-bonus"
											:placeholder="__('bonus')"
											v-model="cell(pl.name, uom, c.name).bonus"
										/>
									</template>
									<span v-else class="cp-muted">—</span>
								</td>
							</template>
						</tr>
						<tr v-if="!visibleCustomers.length">
							<td :colspan="priceLists.length * 2 + 1" class="cp-empty">
								{{ __('No customers to show.') }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<div class="cp-legend">
				<span class="cp-swatch cp-sw-this"></span> {{ __('set by this invoice') }}
				<span class="cp-swatch cp-sw-other"></span> {{ __('set by another invoice') }}
				<span class="cp-swatch cp-sw-dirty"></span> {{ __('edited, not saved') }}
			</div>
		</template>
	</div>
</template>

<script>
import { api } from './api';

const cellKey = (item, priceList, uom, customer) => `${item}::${priceList}::${uom}::${customer}`;

function blankCell() {
	return {
		rate: '',
		bonus: '',
		original_rate: '',
		original_bonus: '',
		source_purchase_invoice: null,
		source_updated_on: null,
		changed_by_this_invoice: false,
	};
}

export default {
	name: 'CustomerPrices',
	props: {
		purchaseInvoice: { type: String, required: true },
	},
	data() {
		return {
			loading: true,
			priceLists: [],
			customers: [],
			items: [],
			cells: {},
			generals: {},
			activeItem: null,
			onlyWithPrice: false,
			showBonus: false,
		};
	},
	computed: {
		activeItemDoc() {
			return this.items.find((i) => i.item_code === this.activeItem) || null;
		},
		unitUom() {
			return this.activeItemDoc ? this.activeItemDoc.unit_uom : null;
		},
		blockUom() {
			return this.activeItemDoc ? this.activeItemDoc.block_uom : null;
		},
		/** Edits survive switching items, so dirt is tracked across the whole grid. */
		dirtyCells() {
			return Object.keys(this.cells)
				.map((k) => ({ key: k, cell: this.cells[k] }))
				.filter(({ cell }) => this.isDirty(cell));
		},
		visibleCustomers() {
			if (!this.onlyWithPrice) return this.customers;
			return this.customers.filter((c) =>
				this.priceLists.some((pl) =>
					[this.unitUom, this.blockUom].some((uom) => {
						if (!uom) return false;
						const cell = this.cells[cellKey(this.activeItem, pl.name, uom, c.name)];
						return cell && cell.original_rate !== '';
					})
				)
			);
		},
	},
	created() {
		this.reload();
	},
	methods: {
		async reload() {
			this.loading = true;
			try {
				const ctx = await api.getContext(this.purchaseInvoice);
				this.priceLists = ctx.price_lists;
				this.customers = ctx.customers;
				this.items = ctx.items;
				if (!this.activeItem || !this.items.some((i) => i.item_code === this.activeItem)) {
					this.activeItem = this.items.length ? this.items[0].item_code : null;
				}
				this.buildGrid(ctx.rows);
			} finally {
				this.loading = false;
			}
		},

		/** Index the sparse stored prices; cells are created lazily as the grid asks. */
		buildGrid(stored) {
			const cells = {};
			const generals = {};
			stored.forEach((r) => {
				if (r.customer) {
					cells[cellKey(r.item_code, r.price_list, r.uom, r.customer)] = {
						rate: String(r.rate),
						bonus: String(r.bonus),
						original_rate: String(r.rate),
						original_bonus: String(r.bonus),
						source_purchase_invoice: r.source_purchase_invoice,
						source_updated_on: r.source_updated_on,
						changed_by_this_invoice: r.changed_by_this_invoice,
					};
				} else {
					generals[`${r.item_code}::${r.price_list}::${r.uom}`] = r.rate;
				}
			});
			this.cells = cells;
			this.generals = generals;
		},

		cell(priceList, uom, customer) {
			const key = cellKey(this.activeItem, priceList, uom, customer);
			if (!this.cells[key]) {
				// Vue 2 cannot see plain property adds, so new cells go in reactively.
				this.$set(this.cells, key, blankCell());
			}
			return this.cells[key];
		},

		generalRate(priceList, uom) {
			if (!uom) return null;
			const rate = this.generals[`${this.activeItem}::${priceList}::${uom}`];
			return rate === undefined ? null : rate;
		},

		isDirty(cell) {
			if (cell.rate === '' || cell.rate === null) return false;
			return cell.rate !== cell.original_rate || cell.bonus !== cell.original_bonus;
		},

		cellClass(priceList, uom, customer) {
			const cell = this.cell(priceList, uom, customer);
			if (this.isDirty(cell)) return 'cp-is-dirty';
			if (cell.changed_by_this_invoice) return 'cp-is-this';
			if (cell.source_purchase_invoice) return 'cp-is-other';
			return '';
		},

		cellTitle(priceList, uom, customer) {
			const cell = this.cell(priceList, uom, customer);
			const parts = [];
			if (cell.original_rate !== '') parts.push(__('Stored: {0}', [cell.original_rate]));
			if (cell.source_purchase_invoice) {
				parts.push(
					cell.changed_by_this_invoice
						? __('Set by this invoice on {0}', [cell.source_updated_on])
						: __('Set by {0} on {1}', [cell.source_purchase_invoice, cell.source_updated_on])
				);
			} else if (cell.original_rate !== '') {
				parts.push(__('Never set from a Purchase Invoice'));
			}
			return parts.join('\n');
		},

		fmt(value) {
			return value === null || value === undefined ? '—' : flt(value, 2);
		},

		eachVisibleCell(priceList, fn) {
			this.visibleCustomers.forEach((c) => {
				[this.unitUom, this.blockUom].forEach((uom) => {
					if (uom) fn(this.cell(priceList, uom, c.name), uom);
				});
			});
		},

		fillFromGeneral(priceList) {
			let filled = 0;
			this.eachVisibleCell(priceList, (cell, uom) => {
				const rate = this.generalRate(priceList, uom);
				if (rate !== null) {
					cell.rate = String(rate);
					filled += 1;
				}
			});
			if (!filled) {
				frappe.show_alert({
					message: __('No general price on {0} for this item.', [priceList]),
					indicator: 'orange',
				});
			}
		},

		applyPercent(priceList) {
			const raw = prompt(__('Percent to apply to {0} (negative for a discount):', [priceList]));
			const pct = parseFloat(raw);
			if (isNaN(pct)) return;

			const factor = (100 + pct) / 100;
			this.eachVisibleCell(priceList, (cell, uom) => {
				// Works off whatever the cell shows, falling back to the general price, so
				// it is usable on customers who have no special price yet.
				const base = parseFloat(cell.rate) || this.generalRate(priceList, uom);
				if (base) cell.rate = (base * factor).toFixed(2);
			});
		},

		/** Only edited cells are sent - untouched customers must not be given a price. */
		collectChanges() {
			return this.dirtyCells.map(({ key, cell }) => {
				const [item_code, price_list, uom, customer] = key.split('::');
				return {
					item_code,
					price_list,
					uom,
					customer,
					rate: parseFloat(cell.rate),
					// Carried through untouched when the bonus column is hidden, so a save
					// never silently writes the field's default of 1.
					bonus: parseFloat(cell.bonus) || 0,
				};
			});
		},

		async save() {
			const changes = this.collectChanges();
			if (!changes.length) {
				frappe.show_alert({ message: __('Nothing changed.'), indicator: 'orange' });
				return null;
			}
			const res = await api.savePrices(this.purchaseInvoice, changes);
			frappe.show_alert({
				message: __('{0} created, {1} updated', [res.created.length, res.updated.length]),
				indicator: 'green',
			});
			await this.reload();
			return res;
		},
	},
};
</script>

<style scoped>
.cp-root {
	font-size: 12px;
}
.cp-empty {
	padding: 16px;
	color: var(--text-muted, #8d99a6);
	text-align: center;
}
.cp-toolbar {
	display: flex;
	align-items: flex-end;
	gap: 12px;
	flex-wrap: wrap;
	padding-bottom: 10px;
	border-bottom: 1px solid var(--border-color, #e2e6e9);
}
.cp-field {
	display: flex;
	flex-direction: column;
	gap: 2px;
}
.cp-field label {
	font-size: 11px;
	color: var(--text-muted, #8d99a6);
	margin: 0;
}
.cp-field select {
	min-width: 260px;
	height: 26px;
	border: 1px solid var(--border-color, #d1d8dd);
	border-radius: 4px;
	background: var(--control-bg, #fff);
	padding: 0 6px;
}
.cp-uominfo {
	padding-bottom: 4px;
	color: var(--text-muted, #8d99a6);
}
.cp-check {
	font-weight: normal;
	margin: 0 0 4px 0;
	display: flex;
	align-items: center;
	gap: 5px;
}
.cp-spacer {
	flex: 1;
}
.cp-dirty {
	color: #b45309;
	font-weight: 600;
	padding-bottom: 4px;
}

/* The grid is wider than the dialog by design - it scrolls inside itself so the
   customer column and the header stay put while the price lists pan. */
.cp-scroll {
	overflow: auto;
	max-height: 58vh;
	margin-top: 8px;
}
.cp-table {
	border-collapse: separate;
	border-spacing: 0;
	white-space: nowrap;
}
.cp-table th,
.cp-table td {
	padding: 2px 5px;
	border-bottom: 1px solid var(--border-color, #f0f2f4);
	text-align: left;
}
.cp-table thead th {
	position: sticky;
	background: var(--card-bg, #fff);
	z-index: 2;
	font-size: 11px;
	color: var(--text-muted, #8d99a6);
	font-weight: 600;
}
.cp-table thead tr:first-child th {
	top: 0;
}
.cp-table thead tr:nth-child(2) th {
	top: 22px;
}
.cp-plhead {
	text-align: center;
	border-left: 1px solid var(--border-color, #e2e6e9);
}
.cp-plname {
	display: inline-block;
	max-width: 150px;
	overflow: hidden;
	text-overflow: ellipsis;
	vertical-align: bottom;
	color: var(--text-color, #36414c);
}
.cp-sub {
	text-align: right;
	font-weight: normal;
}
.cp-mini {
	border: 1px solid var(--border-color, #d1d8dd);
	background: var(--control-bg, #fff);
	border-radius: 3px;
	font-size: 10px;
	line-height: 1;
	padding: 1px 4px;
	margin-left: 2px;
	cursor: pointer;
}
.cp-col-cust {
	position: sticky;
	left: 0;
	background: var(--card-bg, #fff);
	z-index: 1;
	max-width: 200px;
	overflow: hidden;
	text-overflow: ellipsis;
	border-right: 1px solid var(--border-color, #e2e6e9);
}
.cp-table thead .cp-col-cust {
	z-index: 3;
}
.cp-col-num {
	width: 82px;
	text-align: right;
}
.cp-general-row td {
	background: var(--bg-light-gray, #f7f9fa);
	font-weight: 600;
}
.cp-general-row .cp-col-cust {
	background: var(--bg-light-gray, #f7f9fa);
}
.cp-muted {
	color: var(--text-muted, #8d99a6);
}
.cp-input {
	width: 100%;
	height: 22px;
	text-align: right;
	border: 1px solid var(--border-color, #d1d8dd);
	border-radius: 3px;
	background: var(--control-bg, #fff);
	padding: 0 4px;
	font-size: 11px;
}
.cp-bonus {
	margin-top: 2px;
	background: #fafafa;
}
.cp-is-dirty {
	border-color: #f59e0b;
	background: #fffbeb;
}
.cp-is-this {
	border-color: #10b981;
	background: #ecfdf5;
}
.cp-is-other {
	border-color: #cbd5e1;
	background: #f8fafc;
}
.cp-legend {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-top: 8px;
	color: var(--text-muted, #8d99a6);
	font-size: 11px;
}
.cp-swatch {
	display: inline-block;
	width: 10px;
	height: 10px;
	border-radius: 2px;
	margin-left: 10px;
}
.cp-sw-this {
	background: #ecfdf5;
	border: 1px solid #10b981;
}
.cp-sw-other {
	background: #f8fafc;
	border: 1px solid #cbd5e1;
}
.cp-sw-dirty {
	background: #fffbeb;
	border: 1px solid #f59e0b;
}
</style>
