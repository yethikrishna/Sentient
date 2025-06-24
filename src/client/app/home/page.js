"use client"

import React, { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import Sidebar from "@components/Sidebar"
import { IconBook, IconChecklist, IconMenu2 } from "@tabler/icons-react"
import toast from "react-hot-toast"

const HomePage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const router = useRouter()

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user details")
			setUserDetails(await response.json())
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
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
					<h1 className="text-lg font-semibold text-white">Home</h1>
				</header>
				<main className="flex-1 flex flex-col items-center justify-center overflow-y-auto p-4 sm:p-6 text-white">
					<div className="w-full max-w-2xl text-center">
						<h1 className="text-4xl font-bold text-white mb-2">
							Welcome, {userDetails?.given_name || "User"}!
						</h1>
						<p className="text-lg text-gray-400 mb-10">
							What would you like to do today?
						</p>

						<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
							{/* Journal Card */}
							<div
								onClick={() => router.push("/journal")}
								className="bg-neutral-900/50 rounded-lg border border-neutral-700 p-8 cursor-pointer hover:border-lightblue hover:bg-neutral-800 transition-all duration-300 transform hover:-translate-y-1"
							>
								<IconBook className="w-12 h-12 text-lightblue mx-auto mb-4" />
								<h2 className="text-2xl font-semibold text-white mb-2">
									Journal
								</h2>
								<p className="text-gray-400">
									View and manage your daily journal entries.
								</p>
							</div>

							{/* Tasks Card */}
							<div
								onClick={() => router.push("/tasks")}
								className="bg-neutral-900/50 rounded-lg border border-neutral-700 p-8 cursor-pointer hover:border-lightblue hover:bg-neutral-800 transition-all duration-300 transform hover:-translate-y-1"
							>
								<IconChecklist className="w-12 h-12 text-lightblue mx-auto mb-4" />
								<h2 className="text-2xl font-semibold text-white mb-2">
									Tasks
								</h2>
								<p className="text-gray-400">
									View and approve automated tasks and plans.
								</p>
							</div>
						</div>
					</div>
				</main>
			</div>
		</div>
	)
}

export default HomePage
