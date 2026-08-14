/**
 * Camera barcode decoding.
 *
 * Nothing on this bench does camera scanning today, so html5-qrcode is vendored
 * in as a dependency of this app. It is loaded lazily: the decoder is a large
 * chunk and most desk page loads never open the camera.
 */

import { ASSETS, loadScript } from './deps';

let instance = null;
let loader = null;

/** Retail goods are almost all EAN/UPC; the rest cover carton and internal labels. */
function supportedFormats(Html5QrcodeSupportedFormats) {
	return [
		Html5QrcodeSupportedFormats.EAN_13,
		Html5QrcodeSupportedFormats.EAN_8,
		Html5QrcodeSupportedFormats.UPC_A,
		Html5QrcodeSupportedFormats.UPC_E,
		Html5QrcodeSupportedFormats.CODE_128,
		Html5QrcodeSupportedFormats.CODE_39,
		Html5QrcodeSupportedFormats.ITF,
		Html5QrcodeSupportedFormats.QR_CODE,
	];
}

/**
 * Loaded as a UMD script rather than `import('html5-qrcode')` on purpose: the
 * bench's esbuild has no code splitting, so a dynamic import gets inlined and
 * the decoder's 375KB lands in the page bundle whether or not the camera is
 * ever opened. A script tag keeps it genuinely on demand.
 */
function loadLibrary() {
	if (window.Html5Qrcode) return Promise.resolve(window);
	if (!loader) {
		loader = loadScript(`${ASSETS}/html5-qrcode/html5-qrcode.min.js`).then(() => window);
	}
	return loader;
}

export async function startCamera(elementId, onDecode) {
	const lib = await loadLibrary();
	const { Html5Qrcode, Html5QrcodeSupportedFormats } = lib;

	await stopCamera();

	instance = new Html5Qrcode(elementId, {
		formatsToSupport: supportedFormats(Html5QrcodeSupportedFormats),
		verbose: false,
	});

	await instance.start(
		{ facingMode: 'environment' },
		{
			fps: 10,
			// A wide, short box matches the shape of a 1D barcode and cuts the
			// work the decoder does per frame.
			qrbox: (viewfinderWidth, viewfinderHeight) => ({
				width: Math.floor(viewfinderWidth * 0.8),
				height: Math.floor(viewfinderHeight * 0.35),
			}),
			aspectRatio: 1.777,
		},
		(decodedText) => onDecode(decodedText),
		// Per-frame decode misses are the normal case while aiming, not errors.
		() => {}
	);
}

export async function stopCamera() {
	if (!instance) return;
	try {
		await instance.stop();
		instance.clear();
	} catch (e) {
		// Already stopped, or the element went away with the component.
	}
	instance = null;
}
