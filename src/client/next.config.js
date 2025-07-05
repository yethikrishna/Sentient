/** @type {import('next').NextConfig} */
const nextConfig = {
	images: {
		unoptimized: true
	}
}

if (process.env.NODE_ENV === "production") {
	nextConfig.output = "standalone"
}

export default nextConfig
