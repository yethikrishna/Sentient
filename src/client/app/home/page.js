"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"

export default function HomePage() {
	const router = useRouter()
	const { user, isAuthLoading, onboarded } = useAuth()

	useEffect(() => {
		// In self-host mode, user is always "present", just need onboarding status.
		if (onboarded !== null) {
			if (onboarded) {
				router.push("/tasks")
			} else {
				router.push("/onboarding")
			}
		}
	}, [onboarded, router])

	useEffect(() => {
		// Only redirect if auth is loaded, user exists, and onboarding status is determined.
		if (!isAuthLoading && user && onboarded !== null) {
			if (onboarded) {
				router.push("/tasks")
			} else {
				router.push("/onboarding")
			}
		}
	}, [isAuthLoading, user, onboarded, router])

	if (isAuthLoading || onboarded === null) {
		return <div>Loading...</div>
	}

	return <div>Welcome to the Home Page. Redirecting...</div>
}
