<template>
	<div class="ps-scan">
		<div v-show="cameraOn" class="ps-scan__camera">
			<div :id="viewportId" class="ps-scan__viewport" />
			<div class="ps-scan__reticle" />
			<v-btn icon dark class="ps-scan__close" @click="stopCamera">
				<v-icon>mdi-close</v-icon>
			</v-btn>
		</div>

		<div class="ps-scan__bar">
			<v-btn
				:color="cameraOn ? 'grey darken-1' : 'primary'"
				depressed
				large
				class="ps-scan__cam-btn"
				:disabled="disabled"
				@click="toggleCamera"
			>
				<v-icon left>{{ cameraOn ? 'mdi-camera-off' : 'mdi-camera' }}</v-icon>
				{{ cameraOn ? __('Stop') : __('Scan') }}
			</v-btn>

			<v-btn icon large :disabled="disabled" :title="__('Add item by hand')" @click="manual = !manual">
				<v-icon>mdi-magnify</v-icon>
			</v-btn>

			<v-btn icon large :disabled="disabled" :title="__('Create a new item')" @click="$emit('new-item')">
				<v-icon>mdi-plus-box</v-icon>
			</v-btn>
		</div>

		<!-- Always mounted and refocused: a Bluetooth or USB wedge scanner types
		     into whatever holds focus, so this field has to own it. -->
		<input
			ref="wedge"
			v-model="buffer"
			class="ps-scan__wedge"
			:class="{ 'ps-scan__wedge--visible': manual }"
			:placeholder="__('Scan or type a barcode')"
			autocomplete="off"
			autocorrect="off"
			autocapitalize="off"
			spellcheck="false"
			:disabled="disabled"
			@keydown.enter.prevent="submitBuffer"
		/>

		<div v-if="manual" class="ps-scan__manual">
			<v-autocomplete
				v-model="picked"
				:items="results"
				:search-input.sync="query"
				item-text="label"
				item-value="item_code"
				:label="__('Search item by name or code')"
				:no-data-text="__('No matching items')"
				outlined
				dense
				hide-details
				clearable
				@change="onPick"
			/>
		</div>

		<div v-if="error" class="ps-scan__error">
			<v-icon small color="error">mdi-alert</v-icon>
			{{ error }}
		</div>
	</div>
</template>

<script>
import { api } from '../api';
import { startCamera, stopCamera } from '../scanner';

export default {
	name: 'ScanZone',
	props: {
		disabled: { type: Boolean, default: false },
	},

	data() {
		return {
			viewportId: 'ps-camera-viewport',
			cameraOn: false,
			manual: false,
			buffer: '',
			query: null,
			picked: null,
			results: [],
			error: '',
			lastCode: '',
			lastAt: 0,
		};
	},

	watch: {
		query(txt) {
			this.debouncedSearch(txt);
		},
	},

	created() {
		this.debouncedSearch = frappe.utils.debounce(async (txt) => {
			if (!txt || txt.length < 2) {
				this.results = [];
				return;
			}
			const rows = await api.searchItems(txt);
			this.results = rows.map((r) => ({
				...r,
				label: `${r.item_name || r.item_code} — ${r.item_code}`,
			}));
		}, 300);
	},

	mounted() {
		this.rearm();
	},

	beforeDestroy() {
		stopCamera();
	},

	methods: {
		/** Return focus to the wedge field after a dialog or a scan. */
		rearm() {
			if (this.manual) return;
			this.$nextTick(() => {
				const el = this.$refs.wedge;
				if (el && !this.disabled) el.focus();
			});
		},

		submitBuffer() {
			const code = (this.buffer || '').trim();
			this.buffer = '';
			if (code) this.emitCode(code);
		},

		/** Guard against a camera firing the same frame repeatedly, and against a
		 *  wedge scanner double-triggering on one physical scan. */
		emitCode(code) {
			const now = Date.now();
			if (code === this.lastCode && now - this.lastAt < 1500) return;
			this.lastCode = code;
			this.lastAt = now;

			if (navigator.vibrate) navigator.vibrate(40);
			this.$emit('code', code);
		},

		async toggleCamera() {
			if (this.cameraOn) {
				this.stopCamera();
			} else {
				await this.startCamera();
			}
		},

		async startCamera() {
			this.error = '';
			this.cameraOn = true;
			await this.$nextTick();
			try {
				await startCamera(this.viewportId, (code) => this.emitCode(code));
			} catch (e) {
				this.cameraOn = false;
				this.error =
					e && e.name === 'NotAllowedError'
						? __('Camera permission denied. Use a scanner or type the code.')
						: __('Camera unavailable on this device.');
			}
		},

		stopCamera() {
			stopCamera();
			this.cameraOn = false;
			this.rearm();
		},

		onPick(itemCode) {
			if (!itemCode) return;
			this.$emit('pick', itemCode);
			this.picked = null;
			this.query = null;
			this.results = [];
		},
	},
};
</script>

<style scoped>
.ps-scan {
	flex: 0 0 auto;
	background: #ffffff;
	border-bottom: 1px solid #e0e4e6;
}

.ps-scan__camera {
	position: relative;
	width: 100%;
	/* Roughly a third of a phone screen: enough to aim, not so much that the
	   scanned-items list disappears. */
	height: 38vh;
	background: #000000;
	overflow: hidden;
}

.ps-scan__viewport {
	width: 100%;
	height: 100%;
}

.ps-scan__viewport >>> video {
	width: 100% !important;
	height: 100% !important;
	object-fit: cover;
}

.ps-scan__reticle {
	position: absolute;
	top: 50%;
	left: 50%;
	width: 72%;
	height: 34%;
	transform: translate(-50%, -50%);
	border: 2px solid rgba(255, 255, 255, 0.9);
	border-radius: 12px;
	box-shadow: 0 0 0 100vmax rgba(0, 0, 0, 0.35);
	pointer-events: none;
}

.ps-scan__close {
	position: absolute;
	top: 8px;
	right: 8px;
	background: rgba(0, 0, 0, 0.45);
}

.ps-scan__bar {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 12px 16px;
}

.ps-scan__cam-btn {
	flex: 1 1 auto;
}

/* Off-screen but focusable, so a wedge scanner still lands in it. Never
   display:none — that would drop focus and the scan with it. */
.ps-scan__wedge {
	position: absolute;
	width: 1px;
	height: 1px;
	padding: 0;
	border: 0;
	opacity: 0;
	pointer-events: none;
}

.ps-scan__wedge--visible {
	position: static;
	width: calc(100% - 32px);
	height: 48px;
	margin: 0 16px 12px;
	padding: 0 12px;
	border: 1px solid #c4cbd0;
	border-radius: 8px;
	opacity: 1;
	pointer-events: auto;
	/* 16px keeps iOS Safari from zooming the viewport on focus. */
	font-size: 16px;
}

.ps-scan__manual {
	padding: 0 16px 16px;
}

.ps-scan__error {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 0 16px 12px;
	font-size: 13px;
	color: #c62828;
}
</style>
