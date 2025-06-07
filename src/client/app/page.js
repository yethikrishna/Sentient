// src/client/app/page.js
"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useUser } from "@auth0/nextjs-auth0/client"
import AnimatedLogo from "@components/AnimatedLogo"
import toast from "react-hot-toast"
import React from "react"

/**
 * Home Component - The initial loading screen of the application.
 *
 * This component is responsible for checking the user's authentication and onboarding status,
 * then redirecting them to the appropriate page (/api/auth/login, /onboarding, or /chat).
 * It displays a loading animation during this process.
 *
 * @returns {React.ReactNode} - The Home component UI.
 */
const Home = () => {
	const router = useRouter()
	const { user, error: authError, isLoading: isAuthLoading } = useUser()

	const [onboarded, setOnboarded] = useState(null)
	const [isCheckingOnboarding, setIsCheckingOnboarding] = useState(false)

	useEffect(() => {
		if (isAuthLoading) {
			// Still waiting for Auth0 to determine the user's session.
			return
		}

		if (authError) {
			console.error("Authentication error:", authError)
			toast.error("Authentication failed. Please try again.")
			// Redirect to login to re-attempt authentication.
			router.push("/api/auth/login")
			return
		}

		if (!user) {
			// User is not authenticated. Redirect to the Auth0 login page.
			console.log("No user session found, redirecting to login.")
			router.push("/api/auth/login")
			return
		}

		// If we reach here, the user is authenticated. Now, check their onboarding status.
		const checkOnboardingStatus = async () => {
			setIsCheckingOnboarding(true)
			try {
				const response = await fetch("/api/user/data")

				if (response.status === 401) {
					// This case is unlikely if useUser() works but is good to handle.
					toast.error("Session expired. Please log in again.")
					router.push("/api/auth/logout")
					return
				}

				if (!response.ok) {
					const errorData = await response.json()
					throw new Error(
						errorData.message || "Failed to fetch user data"
					)
				}

				const result = await response.json()
				const firstRunCompleted =
					result?.data?.firstRunCompleted ?? false
				setOnboarded(firstRunCompleted)
			} catch (error) {
				toast.error(`Error initializing app: ${error.message}`)
				// Default to sending to onboarding on error for safety.
				setOnboarded(false)
			} finally {
				setIsCheckingOnboarding(false)
			}
		}

		// Only check onboarding if it hasn't been determined yet.
		if (onboarded === null) {
			checkOnboardingStatus()
		}
	}, [isAuthLoading, user, authError, router, onboarded])

	// This effect handles the redirection after onboarding status is known.
	useEffect(() => {
		// Only redirect if auth is loaded, user exists, and onboarding status is determined.
		if (!isAuthLoading && user && onboarded !== null) {
			if (onboarded) {
				router.push("/chat")
			} else {
				router.push("/onboarding")
			}
		}
	}, [isAuthLoading, user, onboarded, router])

	// Show a loading screen while checking authentication or onboarding status.
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
