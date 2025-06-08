"use client"

import { useRouter } from "next/navigation"
import { useEffect } from "react"

/**
 * Update Component - This page was for Electron app updates.
 * It is not used in the web version. Redirecting to home.
 */
const Update = () => {
	const router = useRouter()

	useEffect(() => {
		router.replace("/")
	}, [router])

	return (
		<div className="flex flex-col items-center justify-center min-h-screen bg-black text-white">
			<p>Redirecting...</p>
		</div>
	)
}

export default Update
