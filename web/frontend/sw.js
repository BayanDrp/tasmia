// Service Worker for Tasmia (المسمّع الذكي)
const CACHE_NAME = "tasmia-static-v8";
const ASSETS_TO_CACHE = [
	"/",
	"/recite",
	"/css/style.css",
	"/js/app.js",
	"/manifest.json",
	"/assets/fonts/Amiri-Regular.ttf",
	"/assets/fonts/IBMPlexSansArabic-Regular.ttf"
];

self.addEventListener("install", (event) => {
	event.waitUntil(
		caches.open(CACHE_NAME).then((cache) => {
			return cache.addAll(ASSETS_TO_CACHE).catch(() => {
				// Non-fatal if some assets fail during build/install
			});
		}).then(() => self.skipWaiting())
	);
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches.keys().then((keys) => {
			return Promise.all(
				keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
			);
		}).then(() => self.clients.claim())
	);
});

self.addEventListener("fetch", (event) => {
	const url = new URL(event.request.url);

	// Never cache API calls (Quran text, transcription, audio uploads)
	if (url.pathname.startsWith("/api/")) {
		return;
	}

	// Pages: network first, so a new build is visible immediately.
	// Fall back to the cache when offline.
	if (event.request.mode === "navigate") {
		event.respondWith(
			fetch(event.request)
				.then((response) => {
					if (response && response.status === 200) {
						const copy = response.clone();
						caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
					}
					return response;
				})
				.catch(async () => {
					const cached = (await caches.match(event.request)) || (await caches.match("/recite"));
					return cached || new Response("أنت غير متصل بالإنترنت.", {
						status: 503,
						headers: { "Content-Type": "text/plain; charset=utf-8" }
					});
				})
		);
		return;
	}

	event.respondWith(
		caches.match(event.request).then((cached) => {
			if (cached) {
				// Revalidate in background for static assets
				fetch(event.request).then((response) => {
					if (response && response.status === 200) {
						caches.open(CACHE_NAME).then((cache) => cache.put(event.request, response));
					}
				}).catch(() => {});
				return cached;
			}
			return fetch(event.request).then((response) => {
				if (!response || response.status !== 200 || response.type !== "basic") {
					return response;
				}
				const copy = response.clone();
				caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
				return response;
			}).catch(() => cached || new Response("", { status: 503 }));
		})
	);
});
