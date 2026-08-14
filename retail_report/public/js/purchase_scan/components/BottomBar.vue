<template>
	<div class="ps-bottom ps-safe-bottom">
		<div class="ps-bottom__tally">
			<div class="ps-bottom__num">{{ count }}</div>
			<div class="ps-bottom__label">
				{{ count === 1 ? __('line') : __('lines') }} · {{ formattedQty }} {{ __('units') }}
			</div>
		</div>

		<v-btn
			color="primary"
			depressed
			x-large
			class="ps-bottom__submit"
			:loading="busy"
			:disabled="disabled || busy"
			@click="$emit('submit')"
		>
			{{ __('Create Invoice') }}
		</v-btn>
	</div>
</template>

<script>
export default {
	name: 'BottomBar',
	props: {
		count: { type: Number, default: 0 },
		qty: { type: Number, default: 0 },
		busy: { type: Boolean, default: false },
		disabled: { type: Boolean, default: false },
	},
	computed: {
		formattedQty() {
			return Number.isInteger(this.qty) ? this.qty : this.qty.toFixed(2);
		},
	},
};
</script>

<style scoped>
.ps-bottom {
	display: flex;
	align-items: center;
	gap: 12px;
	flex: 0 0 auto;
	padding: 12px 16px;
	background: #ffffff;
	border-top: 1px solid #e0e4e6;
	box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.06);
}

.ps-bottom__tally {
	flex: 0 0 auto;
	min-width: 72px;
}

.ps-bottom__num {
	font-size: 22px;
	font-weight: 700;
	line-height: 1;
}

.ps-bottom__label {
	font-size: 11px;
	color: #90a4ae;
}

.ps-bottom__submit {
	flex: 1 1 auto;
}
</style>
