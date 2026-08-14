<template>
	<v-bottom-sheet :value="value" persistent scrollable @input="$emit('input', $event)">
		<v-card v-if="item" class="ps-qty">
			<div class="ps-qty__head">
				<div class="ps-qty__name">{{ item.item_name || item.item_code }}</div>
				<div class="ps-qty__code">{{ item.item_code }}</div>
				<div v-if="item.barcode" class="ps-qty__code">{{ item.barcode }}</div>
			</div>

			<div class="ps-qty__body">
				<label class="ps-qty__label">{{ __('Quantity') }}</label>
				<div class="ps-qty__stepper">
					<v-btn icon large :disabled="qty <= 1" @click="bump(-1)">
						<v-icon large>mdi-minus-circle-outline</v-icon>
					</v-btn>
					<input
						ref="qty"
						v-model.number="qty"
						type="number"
						inputmode="decimal"
						min="0"
						step="any"
						class="ps-qty__input"
						@focus="$event.target.select()"
					/>
					<v-btn icon large @click="bump(1)">
						<v-icon large>mdi-plus-circle-outline</v-icon>
					</v-btn>
				</div>

				<label class="ps-qty__label">{{ __('Unit') }}</label>
				<v-select
					v-model="uom"
					:items="item.uoms || [item.uom]"
					outlined
					dense
					hide-details
				/>
			</div>

			<div class="ps-qty__actions ps-safe-bottom">
				<v-btn large text @click="cancel">{{ __('Cancel') }}</v-btn>
				<v-btn large color="primary" depressed :disabled="!valid" @click="confirm">
					{{ __('Add') }}
				</v-btn>
			</div>
		</v-card>
	</v-bottom-sheet>
</template>

<script>
export default {
	name: 'QtySheet',
	props: {
		value: { type: Boolean, default: false },
		item: { type: Object, default: null },
	},

	data() {
		return { qty: 1, uom: null };
	},

	computed: {
		valid() {
			return Number(this.qty) > 0 && !!this.uom;
		},
	},

	watch: {
		value(open) {
			if (!open || !this.item) return;
			this.qty = this.item.qty || 1;
			this.uom = this.item.uom;
			// Phones open the keyboard on focus, which shoves the sheet up; wait for
			// the sheet transition before grabbing it.
			setTimeout(() => {
				const el = this.$refs.qty;
				if (el) el.select();
			}, 350);
		},
	},

	methods: {
		bump(delta) {
			this.qty = Math.max(0, (Number(this.qty) || 0) + delta);
		},
		cancel() {
			this.$emit('input', false);
		},
		confirm() {
			this.$emit('confirm', {
				item_code: this.item.item_code,
				item_name: this.item.item_name,
				barcode: this.item.barcode || '',
				qty: Number(this.qty),
				uom: this.uom,
				uoms: this.item.uoms || [this.uom],
				is_new_item: this.item.is_new_item || 0,
			});
		},
	},
};
</script>

<style scoped>
.ps-qty {
	border-radius: 16px 16px 0 0;
}

.ps-qty__head {
	padding: 20px 20px 12px;
	border-bottom: 1px solid #eceff1;
}

.ps-qty__name {
	font-size: 18px;
	font-weight: 600;
	line-height: 1.3;
}

.ps-qty__code {
	font-size: 13px;
	color: #78909c;
}

.ps-qty__body {
	padding: 16px 20px 8px;
}

.ps-qty__label {
	display: block;
	margin-bottom: 6px;
	font-size: 12px;
	font-weight: 600;
	color: #607d8b;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}

.ps-qty__stepper {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-bottom: 20px;
}

.ps-qty__input {
	flex: 1 1 auto;
	width: 100%;
	height: 60px;
	border: 1px solid #c4cbd0;
	border-radius: 10px;
	text-align: center;
	/* Large enough to read at arm's length, and at/above 16px so iOS Safari
	   does not zoom the viewport when it takes focus. */
	font-size: 28px;
	font-weight: 600;
}

.ps-qty__actions {
	display: grid;
	grid-template-columns: 1fr 2fr;
	gap: 12px;
	padding: 12px 20px 20px;
	border-top: 1px solid #eceff1;
}
</style>
