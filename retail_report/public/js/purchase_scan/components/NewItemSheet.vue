<template>
	<v-bottom-sheet :value="value" persistent scrollable @input="$emit('input', $event)">
		<v-card class="ps-new">
			<div class="ps-new__head">
				<div class="ps-new__title">{{ __('New item') }}</div>
				<div v-if="barcode" class="ps-new__warn">
					<v-icon small color="warning">mdi-alert</v-icon>
					{{ __('Barcode {0} is not in stock yet.', [barcode]) }}
				</div>
			</div>

			<div class="ps-new__body">
				<v-text-field
					ref="name"
					v-model="itemName"
					:label="__('Item name')"
					outlined
					dense
					:hint="__('Saved with a {0} prefix until someone completes the item.', [prefix])"
					persistent-hint
					class="mb-4"
				/>

				<v-text-field
					v-if="!barcode"
					v-model="itemCode"
					:label="__('Item code (optional)')"
					:placeholder="__('Generated if left blank')"
					outlined
					dense
					hide-details
					class="mb-4"
				/>

				<v-autocomplete
					v-model="uom"
					:items="uomOptions"
					:search-input.sync="uomSearch"
					:label="__('Unit of measure')"
					outlined
					dense
					hide-details
				/>
			</div>

			<div class="ps-new__actions ps-safe-bottom">
				<v-btn large text @click="$emit('input', false)">{{ __('Cancel') }}</v-btn>
				<v-btn large color="primary" depressed :disabled="!valid" :loading="busy" @click="create">
					{{ __('Create & add') }}
				</v-btn>
			</div>
		</v-card>
	</v-bottom-sheet>
</template>

<script>
import { api, searchLink } from '../api';

export default {
	name: 'NewItemSheet',
	props: {
		value: { type: Boolean, default: false },
		barcode: { type: String, default: null },
	},

	data() {
		return {
			prefix: 'NEW_01',
			itemName: '',
			itemCode: '',
			uom: 'шт',
			uomOptions: [],
			uomSearch: null,
			busy: false,
		};
	},

	computed: {
		valid() {
			return !!this.itemName.trim() && !!this.uom;
		},
	},

	watch: {
		value(open) {
			if (!open) return;
			this.itemName = '';
			this.itemCode = '';
			setTimeout(() => this.$refs.name && this.$refs.name.focus(), 350);
		},
		uomSearch(txt) {
			this.debouncedUom(txt);
		},
	},

	created() {
		this.debouncedUom = frappe.utils.debounce(async (txt) => {
			this.uomOptions = await searchLink('UOM', txt);
		}, 300);
		this.debouncedUom('');
	},

	methods: {
		async create() {
			this.busy = true;
			try {
				const payload = await api.createItem({
					item_name: this.itemName.trim(),
					uom: this.uom,
					barcode: this.barcode || null,
					item_code: this.itemCode.trim() || null,
				});
				this.$emit('created', payload);
			} catch (e) {
				// frappe.call has already shown the server error dialog.
			} finally {
				this.busy = false;
			}
		},
	},
};
</script>

<style scoped>
.ps-new {
	border-radius: 16px 16px 0 0;
}

.ps-new__head {
	padding: 20px 20px 12px;
	border-bottom: 1px solid #eceff1;
}

.ps-new__title {
	font-size: 18px;
	font-weight: 600;
}

.ps-new__warn {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-top: 6px;
	font-size: 13px;
	color: #ef6c00;
}

.ps-new__body {
	padding: 20px;
}

.ps-new__actions {
	display: grid;
	grid-template-columns: 1fr 2fr;
	gap: 12px;
	padding: 12px 20px 20px;
	border-top: 1px solid #eceff1;
}
</style>
