// src/client/next.config.js

/** @type {import('next').NextConfig} */
import nextPWA from "next-pwa"

const withPWA = nextPWA({
	dest: "public",
	disable: process.env.NODE_ENV === "development",
	register: true,
	skipWaiting: false,
	runtimeCaching: [
		// Cache Google Fonts
		{
			urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
			handler: "CacheFirst",
			options: {
				cacheName: "google-fonts-cache",
				expiration: {
					maxEntries: 10,
					maxAgeSeconds: 60 * 60 * 24 * 365 // 1 year
				},
				cacheableResponse: {
					statuses: [0, 200]
				}
			}
		},
		// Cache API data with a Stale-While-Revalidate strategy
		{
			urlPattern: /\/api\//, // Match any API route
			handler: "StaleWhileRevalidate",
			options: {
				cacheName: "api-data-cache",
				expiration: {
					maxEntries: 50,
					maxAgeSeconds: 60 * 60 // 1 hour
				},
				cacheableResponse: {
					statuses: [200]
				}
			}
		}
	]
})

const nextConfig = {
	images: {
		unoptimized: true
	},
	// Add this section to keep console logs in production builds
	compiler: {
		removeConsole: false
	},
	async rewrites() {
		if (process.env.NEXT_PUBLIC_POSTHOG_KEY) {
			if (process.env.NEXT_PUBLIC_POSTHOG_HOST) {
				// Self-hosted or custom instance
				return [
					{
						source: "/ingest/:path*",
						destination: `${process.env.NEXT_PUBLIC_POSTHOG_HOST}/:path*`
					}
				]
			} else {
				// Default to PostHog US cloud
				return [
					{
						source: "/ingest/static/:path*",
						destination:
							"https://us-assets.i.posthog.com/static/:path*"
					},
					{
						source: "/ingest/:path*",
						destination: "https://us.i.posthog.com/:path*"
					}
				]
			}
		}
		return []
	},
	// This is required to support PostHog trailing slash API requests
	skipTrailingSlashRedirect: true
}

if (process.env.NODE_ENV === "production") {
	nextConfig.output = "standalone"
}

export default withPWA(nextConfig)
