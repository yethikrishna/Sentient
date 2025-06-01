"use client"

import { useState, useEffect } from "react" // Importing necessary React hooks
import { useRouter } from "next/navigation" // Importing the useRouter hook from next/navigation for client-side routing
import AnimatedLogo from "@components/AnimatedLogo" // Component for displaying an animated logo
import toast from "react-hot-toast" // Library for displaying toast notifications
import React from "react"

/**
 * Home Component - The initial loading screen of the application.
 *
 * This component is responsible for initializing the application by fetching user data,
 * and determining whether to navigate the user to the personality test or directly to the chat interface
 * based on their onboarding status. It also displays a loading animation while initializing.
 *
 * @returns {React.ReactNode} - The Home component UI.
 */
const Home = () => {
	// State to track the onboarding status of the user.
	// null: initial state, false: user not onboarded, true: user onboarded
	const [onboarded, setOnboarded] = useState(null) // onboarded: boolean | null
	// State to manage the loading state of the component, displayed during initialization.
	const [loading, setLoading] = useState(true) // loading: boolean
	const router = useRouter() // Initializing the router for navigation

	/**
	 * Initializes the application by fetching user data from the database.
	 *
	 * This function uses Electron's `invoke` to call backend functions to:
	 * 1. Fetch user data from the database to check onboarding status.
	 * 2. Optionally start Neo4j and initiate the FastAPI server (currently commented out).
	 * 3. Update the `loading` and `onboarded` states based on the fetched data.
	 *
	 * @async
	 * @function initializeApp
	 * @returns {Promise<void>}
	 */
	const initializeApp = async () => {
		try {
			// Fetch user data from the database using electron invoke
			const { data: userData } =
				await window.electron?.invoke("get-user-data")

			setLoading(false) // Set loading to false once initialization is complete (or attempted)
			setOnboarded(userData?.firstRunCompleted) // Set onboarded state based on 'firstRunCompleted' from user data
		} catch (error) {
			toast.error(`Error initializing app: ${error}`) // Display error toast if initialization fails
			setLoading(false) // Ensure loading is set to false even if there's an error
		}
	}

	/**
	 * useEffect hook to call `initializeApp` when the component mounts.
	 *
	 * This ensures that the application initialization process starts as soon as the Load component is rendered.
	 */
	useEffect(() => {
		initializeApp() // Call initializeApp function when component mounts
	}, []) // Empty dependency array ensures this effect runs only once on mount

	useEffect(() => {
		if (!loading && onboarded !== null) {
			if (onboarded === false) {
				router.push("/onboarding")
			} else {
				router.push("/chat")
			}
		}
	}, [loading, onboarded, router])

	return (
		<div className="min-h-screen flex flex-col items-center justify-center">
			<div className="flex flex-col items-center justify-center h-full backdrop-blur-xs">
				{/* Render AnimatedLogo and title when not loading */}
				{loading && (
					<>
						<AnimatedLogo /> {/* Animated logo component */}
						<h1 className="text-white text-4xl mt-4">
							Sentient
						</h1>{" "}
						{/* Application title */}
					</>
				)}
			</div>
		</div>
	)
}

export default Home
