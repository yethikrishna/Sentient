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
 * This component is responsible for checking the user's onboarding status
 * and redirecting them to the appropriate page (/onboarding or /chat).
 * It displays a loading animation during this process.
 *
 * @returns {React.ReactNode} - The Home component UI.
 */
const Home = () => {
	// State to track the onboarding status of the user.
	// null: initial state, false: user not onboarded, true: user onboarded
	const [onboarded, setOnboarded] = useState(null)
	// State to manage the loading state of the component.
	const [loading, setLoading] = useState(true)
	const router = useRouter() // Initializing the router for navigation

	/**
	 * Initializes the application by fetching user data to check onboarding status.
	 *
	 * This function fetches user data from the API to determine if the user has
	 * completed the onboarding process (firstRunCompleted).
	 *
	 * @async
	 * @function initializeApp
	 * @returns {Promise<void>}
	 */
	const initializeApp = async () => {
		try {
			const response = await fetch("/api/user/data")
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(
					errorData.message || "Failed to fetch user data"
				)
			}
			const result = await response.json()
			console.log("Home page: get-user-data response:", result?.data)

			// If response.data is undefined or null, or firstRunCompleted is missing, treat as not onboarded.
			const firstRunCompleted = result?.data?.firstRunCompleted
			setOnboarded(firstRunCompleted) // Will be true, false, or undefined
		} catch (error) {
			toast.error(`Error initializing app: ${error.message || error}`)
			console.error("Home page: Error initializing app:", error)
			setOnboarded(undefined) // Treat as not onboarded on error for safety
		} finally {
			setLoading(false) // Set loading to false once initialization is complete.
		}
	}

	/**
	 * useEffect hook to call `initializeApp` when the component mounts.
	 */
	useEffect(() => {
		initializeApp()
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []) // Empty dependency array ensures this effect runs only once on mount

	/**

	 * useEffect hook to navigate the user based on their onboarding status
	 * once loading is complete.
	 */
	useEffect(() => {
		if (!loading) {
			console.log(
				"Home page: Loading complete. Onboarded status:",
				onboarded
			)
			// If onboarding is not explicitly true (i.e., false or undefined), redirect to onboarding.
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
