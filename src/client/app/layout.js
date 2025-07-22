// src/client/app/layout.js
import { Auth0Provider } from "@auth0/nextjs-auth0"
import "@styles/globals.css" // Import global styles for the application
import { Toaster } from "react-hot-toast" // Import Toaster component for displaying toast notifications
import React from "react"
import LayoutWrapper from "@components/LayoutWrapper"
import { PostHogProvider } from "@components/PostHogProvider"

/**
 * Metadata for the RootLayout component.
 * Defines the title and description of the application.
 * These metadata values are used for SEO and browser tab titles.
 */
export const metadata = {
	title: "Sentient", // Title of the application, displayed in browser tab or window title
	description: "Your autopilot for productivity" // Description of the application, used for SEO purposes
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
	return (
		<html lang="en" suppressHydrationWarning>
			<head>
				<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
				<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
				<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
				<link rel="manifest" href="/site.webmanifest" />
			</head>
			<Auth0Provider>
				<body className="font-Inter">
					<PostHogProvider>
						<Toaster position="bottom-right" />
						<LayoutWrapper>{children}</LayoutWrapper>
					</PostHogProvider>
				</body>
			</Auth0Provider>
		</html>
	)
}