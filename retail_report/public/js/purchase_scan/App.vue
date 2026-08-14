<template>
	<v-app>
		<div class="ps-shell">
			<SessionBar
				:session="session"
				:companies="companies"
				:locked="!!items.length"
				@update="onSessionUpdate"
			/>

			<ScanZone
				ref="scanZone"
				:disabled="!sessionReady"
				@code="onCode"
				@pick="onPick"
				@new-item="openNewItem(null)"
			/>

			<ItemList :items="items" @edit="editRow" @remove="removeRow" />

			<BottomBar
				:count="totalLines"
				:qty="totalQty"
				:busy="busy"
				:disabled="!sessionReady || !items.length"
				@submit="submit"
			/>
		</div>

		<QtySheet
			v-model="qtySheet"
			:item="pending"
			@confirm="addRow"
		/>

		<NewItemSheet
			v-model="newItemSheet"
			:barcode="pendingBarcode"
			@created="onItemCreated"
		/>

		<v-snackbar v-model="toast.show" :color="toast.color" timeout="2600" bottom>
			{{ toast.text }}
		</v-snackbar>
	</v-app>
</template>

<script>
import SessionBar from './components/SessionBar.vue';
import ScanZone from './components/ScanZone.vue';
import ItemList from './components/ItemList.vue';
import BottomBar from './components/BottomBar.vue';
import QtySheet from './components/QtySheet.vue';
import NewItemSheet from './components/NewItemSheet.vue';
import { api } from './api';

export default {
	name: 'PurchaseScanApp',
	components: { SessionBar, ScanZone, ItemList, BottomBar, QtySheet, NewItemSheet },

	data() {
		return {
			session: { supplier: null, company: null, warehouse: null, date: null, name: null },
			companies: [],
			items: [],
			busy: false,
			qtySheet: false,
			newItemSheet: false,
			pending: null,
			pendingBarcode: null,
			editingIndex: null,
			toast: { show: false, text: '', color: 'success' },
		};
	},

	computed: {
		sessionReady() {
			const s = this.session;
			return !!(s.supplier && s.company && s.warehouse && s.date);
		},
		totalLines() {
			return this.items.length;
		},
		totalQty() {
			return this.items.reduce((sum, r) => sum + (Number(r.qty) || 0), 0);
		},
	},

	async created() {
		const defaults = await api.getDefaults();
		this.companies = defaults.companies || [];
		this.session = {
			...this.session,
			company: defaults.company,
			warehouse: defaults.warehouse,
			date: defaults.date,
		};
	},

	methods: {
		notify(text, color = 'success') {
			this.toast = { show: true, text, color };
		},

		onSessionUpdate(patch) {
			this.session = { ...this.session, ...patch };
		},

		/** A barcode arrived — from the camera, a wedge scanner, or typed by hand. */
		async onCode(code) {
			if (!this.sessionReady) {
				this.notify(__('Choose supplier, company and warehouse first'), 'warning');
				return;
			}
			try {
				const result = await api.scanLookup(code);
				if (result.found) {
					this.openQty(result);
				} else {
					this.openNewItem(result.barcode);
				}
			} catch (e) {
				this.notify(__('Lookup failed'), 'error');
			}
		},

		/** An item chosen from the manual search list. */
		async onPick(itemCode) {
			const result = await api.scanLookup(itemCode);
			if (result.found) this.openQty(result);
		},

		openQty(payload) {
			this.editingIndex = null;
			this.pending = { ...payload, qty: 1 };
			this.qtySheet = true;
		},

		editRow(index) {
			const row = this.items[index];
			this.editingIndex = index;
			this.pending = { ...row, uoms: row.uoms || [row.uom] };
			this.qtySheet = true;
		},

		openNewItem(barcode) {
			this.pendingBarcode = barcode;
			this.newItemSheet = true;
		},

		onItemCreated(payload) {
			this.newItemSheet = false;
			this.notify(__('Item {0} created', [payload.item_code]));
			this.openQty({ ...payload, is_new_item: 1 });
		},

		addRow(row) {
			this.qtySheet = false;

			if (this.editingIndex !== null) {
				this.$set(this.items, this.editingIndex, row);
				this.editingIndex = null;
			} else {
				// Repeat scans of the same item and UOM accumulate rather than
				// stacking identical lines — matches what the server does on save.
				const existing = this.items.findIndex(
					(r) => r.item_code === row.item_code && r.uom === row.uom
				);
				if (existing > -1) {
					const merged = { ...this.items[existing] };
					merged.qty = (Number(merged.qty) || 0) + (Number(row.qty) || 0);
					this.$set(this.items, existing, merged);
				} else {
					this.items.push(row);
				}
			}

			this.$nextTick(() => this.$refs.scanZone && this.$refs.scanZone.rearm());
		},

		removeRow(index) {
			this.items.splice(index, 1);
		},

		async submit() {
			this.busy = true;
			try {
				const saved = await api.saveSession({ ...this.session, items: this.items });
				this.session = { ...this.session, name: saved.name };

				const result = await api.createInvoice(saved.name);
				this.notify(__('Purchase Invoice {0} created', [result.purchase_invoice]));
				frappe.set_route('Form', 'Purchase Invoice', result.purchase_invoice);
			} catch (e) {
				// Frappe already surfaces the server message; keep the toast short.
				this.notify(__('Could not create the invoice'), 'error');
			} finally {
				this.busy = false;
			}
		},
	},
};
</script>

<style>
/* The desk shell is built for a mouse and a wide screen. On the scanner page we
   claim the whole viewport back. */
body.purchase-scan-active .page-head,
body.purchase-scan-active .navbar,
body.purchase-scan-active .page-container > .page-head {
	display: none !important;
}

body.purchase-scan-active .layout-main-section-wrapper,
body.purchase-scan-active .layout-main-section {
	margin: 0 !important;
	padding: 0 !important;
	border: none !important;
	background: transparent !important;
}

.ps-shell {
	display: flex;
	flex-direction: column;
	/* Small-viewport unit keeps the layout honest when mobile browser chrome
	   slides in and out; the vh value is the fallback for older engines. */
	height: 100vh;
	height: 100svh;
	max-width: 720px;
	margin: 0 auto;
	background: #f5f7f8;
	overflow: hidden;
}

/* Only the item list scrolls. The session bar, scan zone and action bar stay put
   so the operator's thumb always finds them in the same place. */
.ps-scroll {
	flex: 1 1 auto;
	overflow-y: auto;
	-webkit-overflow-scrolling: touch;
	overscroll-behavior: contain;
}

/* Every interactive target clears the 48px touch minimum. */
.ps-shell .v-btn:not(.v-btn--fab):not(.v-btn--icon) {
	min-height: 48px;
}

.ps-safe-bottom {
	padding-bottom: env(safe-area-inset-bottom, 0);
}
</style>
