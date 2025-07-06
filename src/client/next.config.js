// src/client/next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
	images: {
		unoptimized: true
	},
	// Add this section to keep console logs in production builds
	compiler: {
		removeConsole: false
	}
}

if (process.env.NODE_ENV === "production") {
	nextConfig.output = "standalone"
}

export default nextConfig
