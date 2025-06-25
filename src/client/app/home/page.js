"use client"

import React, { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import Sidebar from "@components/Sidebar"
import {
	IconBook,
	IconChecklist,
	IconMenu2,
	IconLoader,
	IconPencil,
	IconPlus
} from "@tabler/icons-react"
import toast from "react-hot-toast"

// A new component for the journal preview
const TodaysJournalPreview = () => {
	const [blocks, setBlocks] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const router = useRouter()

	const fetchTodaysBlocks = async () => {
		setIsLoading(true)
		try {
			const today = new Date().toISOString().split("T")[0]
			const response = await fetch(`/api/journal?date=${today}`)
			if (!response.ok) throw new Error("Failed to fetch today's journal")
			const data = await response.json()
			setBlocks(data.blocks || [])
		} catch (error) {
			toast.error(error.message)
			setBlocks([])
		} finally {
			setIsLoading(false)
		}
	}

	useEffect(() => {
		fetchTodaysBlocks()
	}, [])

	return (
		<div className="mt-12">
			<h2 className="text-2xl font-semibold text-white mb-4">
				Today's Journal
			</h2>
			<div className="bg-neutral-900/50 rounded-lg border border-neutral-700 p-6 min-h-[200px] flex flex-col">
				{isLoading ? (
					<div className="flex-1 flex items-center justify-center">
						<IconLoader className="animate-spin text-lightblue" />
					</div>
				) : blocks.length > 0 ? (
					<ul className="space-y-3">
						{blocks.slice(0, 3).map((block) => (
							<li
								key={block.block_id}
								className="text-gray-300 text-sm pl-4 border-l-2 border-neutral-600"
							>
								{block.content}
							</li>
						))}
						{blocks.length > 3 && (
							<li className="text-gray-500 text-sm italic">
								...and {blocks.length - 3} more entries.
							</li>
						)}
					</ul>
				) : (
					<div className="flex-1 flex flex-col items-center justify-center text-center text-gray-500">
						<IconPencil size={32} className="mb-2" />
						<p>No entries for today yet.</p>
						<p className="text-xs">
							Start writing in your journal!
						</p>
					</div>
				)}
				<button
					onClick={() => router.push("/journal")}
					className="mt-6 self-start flex items-center gap-2 py-2 px-4 rounded-full bg-darkblue hover:bg-lightblue text-white text-xs sm:text-sm font-medium transition-colors shadow-md"
				>
					<IconPlus size={16} />
					Go to Journal
				</button>
			</div>
		</div>
	)
}

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
				<main className="flex-1 overflow-y-auto p-4 sm:p-6 text-white custom-scrollbar">
					<div className="w-full max-w-4xl mx-auto">
						<h1 className="text-4xl font-bold text-white mb-2">
							Welcome, {userDetails?.given_name || "User"}!
						</h1>
						<p className="text-lg text-gray-400 mb-10">
							What would you like to do today?
						</p>

						<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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

						<TodaysJournalPreview />
					</div>
				</main>
			</div>
		</div>
	)
}

export default HomePage
