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
					{{ __('Only customers who already have a price') }}
				</label>
				<div class="cp-spacer"></div>
				<span v-if="dirtyCount" class="cp-dirty">{{ __('{0} unsaved', [dirtyCount]) }}</span>
			</div>

			<div v-for="uom in activeUoms" :key="uom" class="cp-uom">
				<div class="cp-uom-head">
					<strong>{{ uom }}</strong>
					<span class="cp-general">
						{{ __('General price') }}:
						<b>{{ generalRate(uom) === null ? '—' : fmt(generalRate(uom)) }}</b>
					</span>
					<span class="cp-tools">
						<button class="btn btn-xs btn-default" @click="fillFromGeneral(uom)">
							{{ __('Fill from general') }}
						</button>
						<button class="btn btn-xs btn-default" @click="applyPercent(uom, -1)">
							{{ __('− %') }}
						</button>
						<button class="btn btn-xs btn-default" @click="applyPercent(uom, 1)">
							{{ __('+ %') }}
						</button>
						<button class="btn btn-xs btn-default" @click="resetUom(uom)">
							{{ __('Reset') }}
						</button>
					</span>
				</div>

				<table class="cp-table">
					<thead>
						<tr>
							<th class="cp-col-cust">{{ __('Customer') }}</th>
							<th class="cp-col-num">{{ __('Current') }}</th>
							<th class="cp-col-num">{{ __('New Rate') }}</th>
							<th class="cp-col-num">{{ __('Bonus') }}</th>
							<th class="cp-col-src">{{ __('Last set by') }}</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in visibleRows(uom)"
							:key="row.key"
							:class="{ 'cp-changed': isDirty(row) }"
						>
							<td class="cp-col-cust" :title="row.customer">{{ row.customer_name }}</td>
							<td class="cp-col-num cp-muted">
								{{ row.current === null ? '—' : fmt(row.current) }}
							</td>
							<td class="cp-col-num">
								<input
									type="number"
									step="0.01"
									min="0"
									class="cp-input"
									v-model="row.rate"
									:placeholder="generalRate(uom) === null ? '' : String(generalRate(uom))"
								/>
							</td>
							<td class="cp-col-num">
								<input type="number" step="0.01" min="0" class="cp-input" v-model="row.bonus" />
							</td>
							<td class="cp-col-src">
								<span v-if="row.changed_by_this_invoice" class="cp-badge cp-badge-this">
									{{ __('This invoice') }}
								</span>
								<span
									v-else-if="row.source_purchase_invoice"
									class="cp-badge cp-badge-other"
									:title="row.source_updated_on"
								>
									{{ row.source_purchase_invoice }}
								</span>
								<span v-else class="cp-muted">—</span>
							</td>
						</tr>
						<tr v-if="!visibleRows(uom).length">
							<td colspan="5" class="cp-empty-row">{{ __('No customers to show.') }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</template>
	</div>
</template>

<script>
import { api } from './api';

/**
 * One row per (item, uom, customer). `current` is what is stored today and never
 * changes as the operator types - it is what makes "did I already move this?" legible
 * next to the editable value.
 */
function buildRow(item_code, uom, customer, existing) {
	return {
		key: `${item_code}::${uom}::${customer.name}`,
		item_code,
		uom,
		customer: customer.name,
		customer_name: customer.customer_name || customer.name,
		current: existing ? existing.rate : null,
		rate: existing ? String(existing.rate) : '',
		bonus: existing ? String(existing.bonus) : '',
		original_rate: existing ? String(existing.rate) : '',
		original_bonus: existing ? String(existing.bonus) : '',
		source_purchase_invoice: existing ? existing.source_purchase_invoice : null,
		source_updated_on: existing ? existing.source_updated_on : null,
		changed_by_this_invoice: existing ? existing.changed_by_this_invoice : false,
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
			rows: [],
			generals: {},
			activeItem: null,
			onlyWithPrice: false,
		};
	},
	computed: {
		activeUoms() {
			const item = this.items.find((i) => i.item_code === this.activeItem);
			return item ? item.uoms : [];
		},
		dirtyRows() {
			return this.rows.filter((r) => this.isDirty(r));
		},
		dirtyCount() {
			return this.dirtyRows.length;
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

		/** Expand the sparse stored prices into a full item x uom x customer grid. */
		buildGrid(stored) {
			const byKey = {};
			const generals = {};
			stored.forEach((r) => {
				if (r.customer) {
					byKey[`${r.item_code}::${r.uom}::${r.customer}`] = r;
				} else {
					generals[`${r.item_code}::${r.uom}`] = r.rate;
				}
			});
			this.generals = generals;

			const rows = [];
			this.items.forEach((item) => {
				item.uoms.forEach((uom) => {
					this.customers.forEach((c) => {
						rows.push(buildRow(item.item_code, uom, c, byKey[`${item.item_code}::${uom}::${c.name}`]));
					});
				});
			});
			this.rows = rows;
		},

		generalRate(uom) {
			const rate = this.generals[`${this.activeItem}::${uom}`];
			return rate === undefined ? null : rate;
		},

		rowsFor(uom) {
			return this.rows.filter((r) => r.item_code === this.activeItem && r.uom === uom);
		},

		visibleRows(uom) {
			const rows = this.rowsFor(uom);
			return this.onlyWithPrice ? rows.filter((r) => r.current !== null) : rows;
		},

		isDirty(row) {
			if (row.rate === '' || row.rate === null) return false;
			return row.rate !== row.original_rate || row.bonus !== row.original_bonus;
		},

		fmt(value) {
			return format_currency(value, this.currency);
		},

		fillFromGeneral(uom) {
			const rate = this.generalRate(uom);
			if (rate === null) {
				frappe.show_alert({ message: __('No general price for this UOM.'), indicator: 'orange' });
				return;
			}
			this.visibleRows(uom).forEach((r) => {
				r.rate = String(rate);
			});
		},

		applyPercent(uom, sign) {
			const raw = prompt(
				sign < 0 ? __('Discount % off the current rate:') : __('Markup % on the current rate:')
			);
			const pct = parseFloat(raw);
			if (isNaN(pct)) return;

			const factor = (100 + sign * pct) / 100;
			this.visibleRows(uom).forEach((r) => {
				// Percent works off whatever the row shows now, falling back to the general
				// price, so it is usable on customers who have no special price yet.
				const base = parseFloat(r.rate) || this.generalRate(uom);
				if (base) r.rate = (base * factor).toFixed(2);
			});
		},

		resetUom(uom) {
			this.rowsFor(uom).forEach((r) => {
				r.rate = r.original_rate;
				r.bonus = r.original_bonus;
			});
		},

		/** Only edited rows are sent - untouched customers must not be given a price. */
		collectChanges() {
			return this.dirtyRows.map((r) => ({
				item_code: r.item_code,
				uom: r.uom,
				customer: r.customer,
				price_list: this.priceList,
				rate: parseFloat(r.rate),
				bonus: parseFloat(r.bonus) || 0,
			}));
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
	max-height: 62vh;
	overflow: auto;
}
.cp-empty,
.cp-empty-row {
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
	position: sticky;
	top: 0;
	background: var(--card-bg, #fff);
	z-index: 2;
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
	min-width: 190px;
	height: 26px;
	border: 1px solid var(--border-color, #d1d8dd);
	border-radius: 4px;
	background: var(--control-bg, #fff);
	padding: 0 6px;
}
.cp-check {
	font-weight: normal;
	margin: 0 0 3px 0;
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
	padding-bottom: 3px;
}
.cp-uom {
	margin-top: 14px;
}
.cp-uom-head {
	display: flex;
	align-items: center;
	gap: 14px;
	flex-wrap: wrap;
	margin-bottom: 5px;
}
.cp-general {
	color: var(--text-muted, #8d99a6);
}
.cp-tools {
	margin-left: auto;
	display: flex;
	gap: 4px;
}
.cp-table {
	width: 100%;
	border-collapse: collapse;
}
.cp-table th,
.cp-table td {
	padding: 3px 6px;
	border-bottom: 1px solid var(--border-color, #f0f2f4);
	text-align: left;
}
.cp-table th {
	font-size: 11px;
	color: var(--text-muted, #8d99a6);
	font-weight: 600;
}
.cp-col-num {
	width: 96px;
	text-align: right;
}
.cp-col-src {
	width: 150px;
}
.cp-col-cust {
	max-width: 240px;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cp-muted {
	color: var(--text-muted, #8d99a6);
}
.cp-input {
	width: 100%;
	height: 24px;
	text-align: right;
	border: 1px solid var(--border-color, #d1d8dd);
	border-radius: 4px;
	background: var(--control-bg, #fff);
	padding: 0 5px;
}
.cp-changed .cp-input {
	border-color: #f59e0b;
	background: #fffbeb;
}
.cp-badge {
	display: inline-block;
	padding: 1px 6px;
	border-radius: 8px;
	font-size: 10px;
	max-width: 100%;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.cp-badge-this {
	background: #d1fae5;
	color: #065f46;
}
.cp-badge-other {
	background: #eef1f4;
	color: #55606b;
}
</style>
