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
					<label>{{ __('Price List') }}</label>
					<select v-model="priceList" @change="reload">
						<option v-for="pl in priceLists" :key="pl" :value="pl">{{ pl }}</option>
					</select>
				</div>
				<div class="cp-field">
					<label>{{ __('Item') }}</label>
					<select v-model="activeItem">
						<option v-for="it in items" :key="it.item_code" :value="it.item_code">
							{{ it.item_code }} — {{ it.item_name }}
						</option>
					</select>
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
							<th
								v-for="u in activeUoms"
								:key="u.uom"
								:colspan="showBonus ? 3 : 2"
								class="cp-uomhead"
							>
								<b>{{ u.uom }}</b>
								<span v-if="u.conversion_factor !== 1" class="cp-muted">
									× {{ u.conversion_factor }}
								</span>
								<button
									class="cp-mini"
									:title="__('Fill from the general price')"
									@click="fillFromGeneral(u.uom)"
								>=</button>
								<button
									class="cp-mini"
									:title="__('Apply a percentage')"
									@click="applyPercent(u.uom)"
								>%</button>
							</th>
						</tr>
						<tr>
							<template v-for="u in activeUoms">
								<th :key="u.uom + '-c'" class="cp-col-num cp-sub">{{ __('Current') }}</th>
								<th :key="u.uom + '-n'" class="cp-col-num cp-sub">{{ __('New') }}</th>
								<th v-if="showBonus" :key="u.uom + '-b'" class="cp-col-num cp-sub">
									{{ __('Bonus') }}
								</th>
							</template>
						</tr>
					</thead>
					<tbody>
						<tr class="cp-general-row">
							<td class="cp-col-cust">{{ __('General price') }}</td>
							<template v-for="u in activeUoms">
								<td :key="u.uom + '-gc'" class="cp-col-num">{{ fmt(generalRate(u.uom)) }}</td>
								<td :key="u.uom + '-gn'" class="cp-col-num cp-muted">—</td>
								<td v-if="showBonus" :key="u.uom + '-gb'" class="cp-col-num cp-muted">—</td>
							</template>
						</tr>

						<tr v-for="c in visibleCustomers" :key="c.name">
							<td class="cp-col-cust" :title="c.name">{{ c.customer_name || c.name }}</td>
							<template v-for="u in activeUoms">
								<td :key="u.uom + '-c-' + c.name" class="cp-col-num cp-muted">
									{{ cell(u.uom, c.name).original_rate === ''
										? '—'
										: fmt(cell(u.uom, c.name).original_rate) }}
								</td>
								<td :key="u.uom + '-n-' + c.name" class="cp-col-num">
									<input
										type="number"
										step="0.01"
										min="0"
										class="cp-input"
										:class="cellClass(u.uom, c.name)"
										:title="cellTitle(u.uom, c.name)"
										v-model="cell(u.uom, c.name).rate"
									/>
								</td>
								<td v-if="showBonus" :key="u.uom + '-b-' + c.name" class="cp-col-num">
									<input
										type="number"
										step="0.01"
										min="0"
										class="cp-input"
										v-model="cell(u.uom, c.name).bonus"
									/>
								</td>
							</template>
						</tr>
						<tr v-if="!visibleCustomers.length">
							<td :colspan="activeUoms.length * (showBonus ? 3 : 2) + 1" class="cp-empty">
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

const cellKey = (item, uom, customer) => `${item}::${uom}::${customer}`;

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
			priceList: null,
			priceLists: [],
			currency: null,
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
		activeUoms() {
			return this.activeItemDoc ? this.activeItemDoc.uoms : [];
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
				this.activeUoms.some((u) => {
					const cell = this.cells[cellKey(this.activeItem, u.uom, c.name)];
					return cell && cell.original_rate !== '';
				})
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
				const ctx = await api.getContext(this.purchaseInvoice, this.priceList);
				this.priceList = ctx.price_list;
				this.priceLists = ctx.price_lists;
				this.currency = ctx.currency;
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
					cells[cellKey(r.item_code, r.uom, r.customer)] = {
						rate: String(r.rate),
						bonus: String(r.bonus),
						original_rate: String(r.rate),
						original_bonus: String(r.bonus),
						source_purchase_invoice: r.source_purchase_invoice,
						source_updated_on: r.source_updated_on,
						changed_by_this_invoice: r.changed_by_this_invoice,
					};
				} else {
					generals[`${r.item_code}::${r.uom}`] = r.rate;
				}
			});
			this.cells = cells;
			this.generals = generals;
		},

		cell(uom, customer) {
			const key = cellKey(this.activeItem, uom, customer);
			if (!this.cells[key]) {
				// Vue 2 cannot see plain property adds, so new cells go in reactively.
				this.$set(this.cells, key, blankCell());
			}
			return this.cells[key];
		},

		generalRate(uom) {
			const rate = this.generals[`${this.activeItem}::${uom}`];
			return rate === undefined ? null : rate;
		},

		isDirty(cell) {
			if (cell.rate === '' || cell.rate === null) return false;
			return cell.rate !== cell.original_rate || cell.bonus !== cell.original_bonus;
		},

		cellClass(uom, customer) {
			const cell = this.cell(uom, customer);
			if (this.isDirty(cell)) return 'cp-is-dirty';
			if (cell.changed_by_this_invoice) return 'cp-is-this';
			if (cell.source_purchase_invoice) return 'cp-is-other';
			return '';
		},

		cellTitle(uom, customer) {
			const cell = this.cell(uom, customer);
			const parts = [];
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
			return value === null || value === undefined || value === '' ? '—' : flt(value, 2);
		},

		eachVisibleCell(uom, fn) {
			this.visibleCustomers.forEach((c) => fn(this.cell(uom, c.name)));
		},

		fillFromGeneral(uom) {
			const rate = this.generalRate(uom);
			if (rate === null) {
				frappe.show_alert({
					message: __('No general price on {0} for {1}.', [this.priceList, uom]),
					indicator: 'orange',
				});
				return;
			}
			this.eachVisibleCell(uom, (cell) => {
				cell.rate = String(rate);
			});
		},

		applyPercent(uom) {
			const raw = prompt(__('Percent to apply to {0} (negative for a discount):', [uom]));
			const pct = parseFloat(raw);
			if (isNaN(pct)) return;

			const factor = (100 + pct) / 100;
			this.eachVisibleCell(uom, (cell) => {
				// Works off whatever the cell shows, falling back to the general price, so
				// it is usable on customers who have no special price yet.
				const base = parseFloat(cell.rate) || this.generalRate(uom);
				if (base) cell.rate = (base * factor).toFixed(2);
			});
		},

		/** Only edited cells are sent - untouched customers must not be given a price. */
		collectChanges() {
			return this.dirtyCells.map(({ key, cell }) => {
				const [item_code, uom, customer] = key.split('::');
				return {
					item_code,
					uom,
					customer,
					price_list: this.priceList,
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
	min-width: 220px;
	height: 26px;
	border: 1px solid var(--border-color, #d1d8dd);
	border-radius: 4px;
	background: var(--control-bg, #fff);
	padding: 0 6px;
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

/* Wide items scroll inside the grid so the customer column and the header stay put. */
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
	padding: 2px 6px;
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
.cp-uomhead {
	text-align: center;
	border-left: 1px solid var(--border-color, #e2e6e9);
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
	max-width: 230px;
	overflow: hidden;
	text-overflow: ellipsis;
	border-right: 1px solid var(--border-color, #e2e6e9);
}
.cp-table thead .cp-col-cust {
	z-index: 3;
}
.cp-col-num {
	width: 92px;
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
