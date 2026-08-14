<template>
	<div class="ps-session" :class="{ 'ps-session--open': open }">
		<!-- Collapsed: one tappable line, so the scan zone keeps the screen. -->
		<div v-if="!open" class="ps-session__summary" @click="open = true">
			<div class="ps-session__text">
				<div class="ps-session__supplier">
					{{ session.supplier || __('Choose supplier') }}
				</div>
				<div class="ps-session__meta">
					{{ session.warehouse || __('no warehouse') }} · {{ session.date }}
				</div>
			</div>
			<v-icon>mdi-chevron-down</v-icon>
		</div>

		<div v-else class="ps-session__form">
			<v-autocomplete
				:value="session.supplier"
				:items="supplierOptions"
				:search-input.sync="supplierSearch"
				:label="__('Supplier')"
				prepend-inner-icon="mdi-truck"
				outlined
				dense
				hide-details
				clearable
				class="mb-3"
				@change="emit('supplier', $event)"
			/>

			<v-autocomplete
				:value="session.warehouse"
				:items="warehouseOptions"
				:search-input.sync="warehouseSearch"
				:label="__('Warehouse')"
				prepend-inner-icon="mdi-warehouse"
				outlined
				dense
				hide-details
				class="mb-3"
				@change="emit('warehouse', $event)"
			/>

			<div class="ps-session__row">
				<v-select
					:value="session.company"
					:items="companies"
					:label="__('Company')"
					prepend-inner-icon="mdi-domain"
					outlined
					dense
					hide-details
					:disabled="locked"
					@change="emit('company', $event)"
				/>
				<v-text-field
					:value="session.date"
					type="date"
					:label="__('Date')"
					outlined
					dense
					hide-details
					@change="emit('date', $event)"
				/>
			</div>

			<v-btn text block color="primary" class="mt-2" @click="open = false">
				{{ __('Done') }}
			</v-btn>
		</div>
	</div>
</template>

<script>
import { searchLink } from '../api';

export default {
	name: 'SessionBar',
	props: {
		session: { type: Object, required: true },
		companies: { type: Array, default: () => [] },
		// Company must not change once stock has been scanned against it.
		locked: { type: Boolean, default: false },
	},

	data() {
		return {
			// Starts open because nothing can be scanned until it is filled in.
			open: true,
			supplierOptions: [],
			warehouseOptions: [],
			supplierSearch: null,
			warehouseSearch: null,
		};
	},

	watch: {
		supplierSearch(txt) {
			this.debouncedSupplier(txt);
		},
		warehouseSearch(txt) {
			this.debouncedWarehouse(txt);
		},
	},

	created() {
		this.debouncedSupplier = frappe.utils.debounce(async (txt) => {
			this.supplierOptions = await searchLink('Supplier', txt);
		}, 300);

		this.debouncedWarehouse = frappe.utils.debounce(async (txt) => {
			this.warehouseOptions = await searchLink('Warehouse', txt, { is_group: 0 });
		}, 300);

		this.debouncedSupplier('');
		this.debouncedWarehouse('');
	},

	methods: {
		emit(field, value) {
			this.$emit('update', { [field]: value });
		},
	},
};
</script>

<style scoped>
.ps-session {
	flex: 0 0 auto;
	background: #ffffff;
	border-bottom: 1px solid #e0e4e6;
	padding: env(safe-area-inset-top, 0) 0 0;
}

.ps-session__summary {
	display: flex;
	align-items: center;
	gap: 12px;
	min-height: 56px;
	padding: 8px 16px;
	cursor: pointer;
}

.ps-session__text {
	flex: 1 1 auto;
	min-width: 0;
}

.ps-session__supplier {
	font-size: 16px;
	font-weight: 600;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.ps-session__meta {
	font-size: 13px;
	color: #6b7780;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.ps-session__form {
	padding: 16px;
}

.ps-session__row {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 12px;
}
</style>
