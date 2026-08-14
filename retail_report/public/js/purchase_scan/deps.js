/**
 * Vuetify is a ~500KB dependency that only this one page needs.
 *
 * `marinowka` already injects it into every desk page on some sites, so we check
 * before loading rather than shipping a second copy — and on sites without
 * marinowka we load it here instead of in `app_include_js`, which would put it
 * on every page load for the sake of one scanner.
 */

export const ASSETS = '/assets/retail_report/node_modules';

export function loadScript(src) {
	return new Promise((resolve, reject) => {
		const el = document.createElement('script');
		el.src = src;
		el.onload = resolve;
		el.onerror = () => reject(new Error(`Failed to load ${src}`));
		document.head.appendChild(el);
	});
}

function loadStyle(href) {
	if (document.querySelector(`link[href="${href}"]`)) return;
	const el = document.createElement('link');
	el.rel = 'stylesheet';
	el.href = href;
	document.head.appendChild(el);
}

let pending = null;

export function ensureVuetify() {
	if (window.Vuetify) return Promise.resolve();
	if (pending) return pending;

	pending = loadScript(`${ASSETS}/vuetify/dist/vuetify.js`).then(() => {
		loadStyle(`${ASSETS}/vuetify/dist/vuetify.min.css`);
		loadStyle(`${ASSETS}/@mdi/font/css/materialdesignicons.min.css`);
	});

	return pending;
}

export function ensureStyles() {
	loadStyle(`${ASSETS}/vuetify/dist/vuetify.min.css`);
	loadStyle(`${ASSETS}/@mdi/font/css/materialdesignicons.min.css`);
}
