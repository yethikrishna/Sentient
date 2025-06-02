import "@styles/globals.css" // Import global styles for the application
import { Toaster } from "react-hot-toast" // Import Toaster component for displaying toast notifications
import React from "react"

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
export default async function RootLayout({ children }) {
		useEffect(() => {
			let intervalId;
			const sendHeartbeat = () => {
				if (document.hasFocus() && window.electron && typeof window.electron.sendUserActivityHeartbeat === 'function') {
					console.log("Client: Sending activity heartbeat...");
					window.electron.sendUserActivityHeartbeat().catch(err => console.error("Heartbeat IPC error:", err));
				}
			};

			// Send heartbeat immediately on mount (if focused) and then every 5 minutes
			sendHeartbeat();
			intervalId = setInterval(sendHeartbeat, 5 * 60 * 1000); // 5 minutes

			// Also send on window focus
			const handleFocus = () => {
				console.log("Client: Window focused, sending heartbeat.");
				sendHeartbeat();
			};
			window.addEventListener('focus', handleFocus);

			return () => {
				clearInterval(intervalId);
				window.removeEventListener('focus', handleFocus);
			};
		}, []); // Empty dependency array means this runs once on mount and cleans up on unmount

		return (
			<html lang="en" suppressHydrationWarning>
				{/* Root html element with language set to English and hydration warning suppressed */}
				<body className="bg-black">
					{/* Body element with a black background using global styles */}
					<Toaster position="bottom-right" />
					{/* Toaster component for displaying notifications, positioned at the bottom-right */}
					{children}
					{/* Render the child components, which is the main content of the application */}
				</body>
			</html>
		)
}