"use client"

import React, { useState, useEffect, useCallback } from "react"
import Sidebar from "@components/Sidebar"
import { IconBook, IconMenu2, IconLoader } from "@tabler/icons-react"
import toast from "react-hot-toast"

const JournalPage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [isLoading, setIsLoading] = useState(true)

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user details")
			setUserDetails(await response.json())
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchUserDetails()
	}, [fetchUserDetails])

	return (
		<div className="flex h-screen bg-matteblack dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col overflow-hidden">
				<header className="flex items-center justify-between p-4 bg-matteblack border-b border-neutral-800 md:hidden">
					<button
						onClick={() => setSidebarVisible(true)}
						className="text-white"
					>
						<IconMenu2 />
					</button>
					<h1 className="text-lg font-semibold text-white">
						Journal
					</h1>
				</header>
				<main className="flex-1 flex flex-col items-center justify-center overflow-y-auto p-4 sm:p-6 text-white relative">
					{isLoading ? (
						<IconLoader className="w-10 h-10 animate-spin text-lightblue" />
					) : (
						<div className="text-center p-6 sm:p-8 bg-neutral-900/50 rounded-lg border border-neutral-700 shadow-xl max-w-2xl w-full">
							<IconBook className="w-16 h-16 text-lightblue mx-auto mb-6" />
							<h1 className="font-Poppins text-white text-3xl sm:text-4xl font-light mb-4">
								Journal Page
							</h1>
							<p className="text-gray-400 text-sm mb-6">
								This is a placeholder for the journal. Feature
								development is in progress.
							</p>
						</div>
					)}
				</main>
			</div>
		</div>
	)
}

export default JournalPage
