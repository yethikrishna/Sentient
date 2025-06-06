// src/client/app/layout.js
import "@styles/globals.css" // Import global styles for the application
import { Toaster } from "react-hot-toast" // Import Toaster component for displaying toast notifications
import React from "react" // No longer need useEffect here

/**
 * Metadata for the RootLayout component.
 * Defines the title and description of the application.
 * These metadata values are used for SEO and browser tab titles.
 */
export const metadata = {
	title: "Sentient", // Title of the application, displayed in browser tab or window title
	description: "Your personal & private AI companion with agents & memory" // Description of the application, used for SEO purposes
}

/**
 * RootLayout Component - The root layout for the entire application.
 *
 * This component wraps the entire application and sets up the basic structure,
 * including global styles, a Toaster for notifications, and the main content area.
 * It is a Server Component in Next.js, indicated by the `async` keyword.
 *
 * @param {object} props - The component props.
 * @param {React.ReactNode} props.children - The child components that represent the application's content.
 * @returns {React.ReactNode} - The RootLayout component UI.
 */
export default function RootLayout({ children }) {
	// Removed the useEffect hook that was sending Electron-specific heartbeats.
	// This functionality is not applicable in a web-only environment.

	return (
		<html lang="en" suppressHydrationWarning>
			<body className="bg-black">
				<Toaster position="bottom-right" />
				{children}
			</body>
		</html>
	)
}
