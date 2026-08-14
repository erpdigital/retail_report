<template>
	<div class="ps-scroll ps-list">
		<div v-if="!items.length" class="ps-list__empty">
			<v-icon size="56" color="#b0bec5">mdi-barcode-scan</v-icon>
			<p>{{ __('Nothing scanned yet') }}</p>
			<span>{{ __('Point the camera at a barcode, or use a scanner.') }}</span>
		</div>

		<div v-for="(row, index) in items" :key="row.item_code + row.uom" class="ps-row">
			<div class="ps-row__main" @click="$emit('edit', index)">
				<div class="ps-row__name">
					{{ row.item_name || row.item_code }}
					<v-chip v-if="row.is_new_item" x-small color="warning" class="ml-1">
						{{ __('new') }}
					</v-chip>
				</div>
				<div class="ps-row__meta">{{ row.item_code }}</div>
			</div>

			<div class="ps-row__qty" @click="$emit('edit', index)">
				<div class="ps-row__num">{{ format(row.qty) }}</div>
				<div class="ps-row__uom">{{ row.uom }}</div>
			</div>

			<v-btn icon class="ps-row__del" :aria-label="__('Remove')" @click="$emit('remove', index)">
				<v-icon color="#90a4ae">mdi-close</v-icon>
			</v-btn>
		</div>
	</div>
</template>

<script>
export default {
	name: 'ItemList',
	props: {
		items: { type: Array, default: () => [] },
	},
	methods: {
		format(qty) {
			const n = Number(qty) || 0;
			// Whole numbers are the common case and read better without a tail.
			return Number.isInteger(n) ? n : n.toFixed(2);
		},
	},
};
</script>

<style scoped>
.ps-list {
	background: #f5f7f8;
}

.ps-list__empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	height: 100%;
	padding: 40px 32px;
	text-align: center;
	color: #78909c;
}

.ps-list__empty p {
	margin: 16px 0 4px;
	font-size: 16px;
	font-weight: 600;
}

.ps-list__empty span {
	font-size: 13px;
}

.ps-row {
	display: flex;
	align-items: center;
	gap: 8px;
	min-height: 64px;
	padding: 10px 8px 10px 16px;
	background: #ffffff;
	border-bottom: 1px solid #eceff1;
}

.ps-row__main {
	flex: 1 1 auto;
	min-width: 0;
}

.ps-row__name {
	font-size: 15px;
	font-weight: 600;
	line-height: 1.3;
	/* Two lines of item name, then ellipsis — long names are the norm here. */
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}

.ps-row__meta {
	font-size: 12px;
	color: #90a4ae;
}

.ps-row__qty {
	flex: 0 0 auto;
	min-width: 56px;
	text-align: right;
}

.ps-row__num {
	font-size: 18px;
	font-weight: 700;
}

.ps-row__uom {
	font-size: 11px;
	color: #90a4ae;
	text-transform: uppercase;
}

.ps-row__del {
	flex: 0 0 auto;
}
</style>
