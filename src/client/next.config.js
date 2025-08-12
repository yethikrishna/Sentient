// src/client/next.config.js

/** @type {import('next').NextConfig} */

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

export default nextConfig
