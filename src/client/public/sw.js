// Import the Workbox libraries from a CDN.
// This is the modern way to use Workbox without a complex build setup.
importScripts(
	"https://storage.googleapis.com/workbox-cdn/releases/6.5.4/workbox-sw.js"
)

// ---------------------------------------------------------------- //
// This is the core Workbox logic that next-pwa was doing for you.
// ---------------------------------------------------------------- //

// This will be populated by next-pwa with the list of all your app's files.
// Even though we removed next-pwa, this placeholder is useful if you ever add it back
// or use another build tool. For now, we'll handle offline manually.
// workbox.precaching.precacheAndRoute(self.__WB_MANIFEST || []);

// --- Caching Strategies ---

// Cache the Google Fonts stylesheets with a stale-while-revalidate strategy.
workbox.routing.registerRoute(
	({ url }) => url.origin === "https://fonts.googleapis.com",
	new workbox.strategies.StaleWhileRevalidate({
		cacheName: "google-fonts-stylesheets"
	})
)

// Cache the underlying font files with a cache-first strategy for 1 year.
workbox.routing.registerRoute(
	({ url }) => url.origin === "https://fonts.gstatic.com",
	new workbox.strategies.CacheFirst({
		cacheName: "google-fonts-webfonts",
		plugins: [
			new workbox.cacheableResponse.CacheableResponsePlugin({
				statuses: [0, 200]
			}),
			new workbox.expiration.ExpirationPlugin({
				maxAgeSeconds: 60 * 60 * 24 * 365,
				maxEntries: 30
			})
		]
	})
)

// Cache Next.js pages with a Network First strategy.
// This ensures users get the latest content but can view cached pages offline.
workbox.routing.registerRoute(
	({ request }) => request.mode === "navigate",
	new workbox.strategies.NetworkFirst({
		cacheName: "pages-cache"
	})
)

// Cache API calls with a Stale-While-Revalidate strategy.
// This provides fast responses from cache while updating in the background.
workbox.routing.registerRoute(
	({ url }) => url.pathname.startsWith("/api/"),
	new workbox.strategies.StaleWhileRevalidate({
		cacheName: "api-data-cache",
		plugins: [
			new workbox.expiration.ExpirationPlugin({
				maxEntries: 50,
				maxAgeSeconds: 60 * 60 // 1 hour
			})
		]
	})
)

// ---------------------------------------------------------------- //
// --- Push Notification Logic ---
// ---------------------------------------------------------------- //

// On install, activate immediately.
self.addEventListener("install", (event) => {
	event.waitUntil(self.skipWaiting())
})

// On activate, take control of all clients.
self.addEventListener("activate", (event) => {
	event.waitUntil(self.clients.claim())
})

// Listen for push notifications.
self.addEventListener("push", (event) => {
	const data = event.data.json()
	const options = {
		body: data.body,
		icon: "/android-chrome-192x192.png",
		badge: "/images/half-logo-dark.svg",
		data: {
			url: data.data.url // URL to open on click, sent from the server
		}
	}
	event.waitUntil(self.registration.showNotification(data.title, options))
})

// Handle notification clicks.
self.addEventListener("notificationclick", (event) => {
	event.notification.close()
	const urlToOpen = new URL(event.notification.data.url, self.location.origin)
		.href

	event.waitUntil(
		clients
			.matchAll({
				type: "window",
				includeUncontrolled: true
			})
			.then((windowClients) => {
				const matchingClient = windowClients.find((client) => {
					return (
						new URL(client.url).pathname ===
						new URL(urlToOpen).pathname
					)
				})

				if (matchingClient) {
					return matchingClient.focus()
				} else {
					return clients.openWindow(urlToOpen)
				}
			})
	)
})
