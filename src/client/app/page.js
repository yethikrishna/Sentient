// src/client/app/page.js
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
	const [onboarded, setOnboarded] = useState(null) // onboarded: boolean | null | undefined
	// State to manage the loading state of the component, displayed during initialization.
	const [loading, setLoading] = useState(true) // loading: boolean
	const router = useRouter() // Initializing the router for navigation

	/**
	 * Initializes the application by fetching user data from the database.
	 *
	 * This function uses Electron's `invoke` to call backend functions to:
	 * 1. Fetch user data from the database to check onboarding status.
	 * 2. Update the `loading` and `onboarded` states based on the fetched data.
	 *
	 * @async
	 * @function initializeApp
	 * @returns {Promise<void>}
	 */
	const initializeApp = async () => {
		try {
			const response = await window.electron?.invoke("get-user-data")
			console.log(
				"Home page: get-user-data response:",
				response?.data
			)

			// If response.data is undefined or null, or firstRunCompleted is missing, treat as not onboarded for this page's logic
			const firstRunCompleted = response?.data?.firstRunCompleted
			setOnboarded(firstRunCompleted) // Will be true, false, or undefined
		} catch (error) {
			toast.error(`Error initializing app: ${error.message || error}`)
			console.error("Home page: Error initializing app:", error)
			setOnboarded(undefined) // Treat as not onboarded on error for safety
		} finally {
			setLoading(false) // Set loading to false once initialization is complete (or attempted)
		}
	}

	/**
	 * useEffect hook to call `initializeApp` when the component mounts.
	 *
	 * This ensures that the application initialization process starts as soon as the Home component is rendered.
	 */
	useEffect(() => {
		initializeApp() // Call initializeApp function when component mounts
	}, []) // Empty dependency array ensures this effect runs only once on mount

	/**
	 * useEffect hook to navigate the user based on their onboarding status once loading is complete.
	 * The actual navigation decision is primarily handled by `main/index.js -> checkValidity` on app start.
	 * This client-side check serves as a fallback or secondary check if the user lands on "/"
	 * after the initial load.
	 */
	useEffect(() => {
		if (!loading) {
			console.log(
				"Home page: Loading complete. Onboarded status:",
				onboarded
			)
			// If onboarding is not explicitly true (i.e., false or undefined), redirect to onboarding.
			// This aligns with the expectation that if firstRunCompleted isn't true, user needs onboarding.
			if (onboarded !== true) {
				console.log("Home page: Pushing to /onboarding")
				router.push("/onboarding")
			} else {
				console.log("Home page: Pushing to /chat")
				router.push("/chat")
			}
		}
	}, [loading, onboarded, router])

	// Display loading animation while fetching data or redirecting.
	return (
		<div className="min-h-screen flex flex-col items-center justify-center bg-black">
			<div className="flex flex-col items-center justify-center h-full backdrop-blur-xs">
				<AnimatedLogo />
				<h1 className="text-white text-4xl mt-4">Sentient</h1>
			</div>
		</div>
	)
}

export default Home