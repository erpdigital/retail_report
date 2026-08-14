import App from './App.vue';
import { ensureVuetify, ensureStyles } from './deps';

frappe.provide('frappe.RetailReport');

frappe.RetailReport.purchase_scan = class {
	constructor(page) {
		this.page = page;
		this.$parent = $(document);
		this.boot();
	}

	async boot() {
		await ensureVuetify();
		ensureStyles();
		this.make_body();
	}

	make_body() {
		this.$el = this.$parent.find('.main-section');
		this.vue = new Vue({
			vuetify: new Vuetify({
				rtl: frappe.utils.is_rtl(),
				theme: {
					themes: {
						light: {
							primary: '#0097A7',
							secondary: '#00BCD4',
							accent: '#9575CD',
							success: '#43A047',
							info: '#2196F3',
							warning: '#FB8C00',
							error: '#E53935',
						},
					},
				},
			}),
			el: this.$el[0],
			render: (h) => h(App),
		});
	}
};
