export default function manifest() {
    return {
		name: "Sentient",
		short_name: "Sentient",
		description: "Your autopilot for productivity",
		start_url: "/",
		display: "standalone",
		background_color: "#000000",
		theme_color: "#F1A21D",
		icons: [
			{
				src: "/android-chrome-192x192.png",
				sizes: "192x192",
				type: "image/png"
			},
			{
				src: "/android-chrome-512x512.png",
				sizes: "512x512",
				type: "image/png"
			},
			{
				src: "/maskable-icon-512x512.png",
				sizes: "512x512",
				type: "image/png",
				purpose: "any maskable"
			}
		]
	}
}
