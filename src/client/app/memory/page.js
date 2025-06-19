"use client"

import React, { useState, useEffect, useCallback } from "react"
import Sidebar from "@components/Sidebar"
import {
	IconBrain,
	IconLoader,
	IconLink,
	IconSettings
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { useRouter } from "next/navigation"

const Memories = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [isMemoryConnected, setIsMemoryConnected] = useState(false)
	const [isLoading, setIsLoading] = useState(true)
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

	const checkMemoryConnection = useCallback(async () => {
		setIsLoading(true)
		try {
			const response = await fetch("/api/user/data")
			if (!response.ok) {
				throw new Error("Could not fetch user data.")
			}
			const result = await response.json()
			setIsMemoryConnected(!!result?.data?.supermemory_user_id)
		} catch (error) {
			toast.error("Could not verify memory connection.")
			setIsMemoryConnected(false)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchUserDetails()
		checkMemoryConnection()
	}, [fetchUserDetails, checkMemoryConnection])

	return (
		<div className="h-screen bg-matteblack flex relative overflow-hidden dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-grow flex flex-col h-full bg-matteblack text-white relative overflow-hidden p-6 gap-4 items-center justify-center">
				<div className="text-center p-8 bg-neutral-900/50 rounded-lg border border-neutral-700 shadow-xl max-w-2xl">
					<IconBrain className="w-16 h-16 text-lightblue mx-auto mb-6" />{" "}
					{/* Adjusted Icon */}
					<h1 className="font-Poppins text-white text-4xl font-light mb-4">
						Universal Memory
					</h1>{" "}
					{/* Adjusted Title */}
					{isLoading ? (
						<div className="flex justify-center items-center h-24">
							<IconLoader className="w-8 h-8 animate-spin text-lightblue" />
						</div>
					) : isMemoryConnected ? (
						<div>
							<p className="text-gray-300 mb-2">
								Your memory is connected and managed by
								Supermemory.
							</p>
							<p className="text-gray-400 text-sm mb-6">
								All your conversations are now part of a
								universal memory layer, accessible across any
								supported platform.
							</p>
							<div className="inline-flex items-center gap-2 bg-green-900/50 text-green-300 text-sm py-2 px-4 rounded-full border border-green-700">
								<IconLink size={16} />
								<span>Connected</span>
							</div>{" "}
							{/* Adjusted Icon */}
						</div>
					) : (
						<div>
							<p className="text-yellow-300 mb-2">
								Your universal memory is not connected.
							</p>
							<p className="text-gray-500 text-sm mb-6">
								This might be an issue with your account
								configuration. Please try refreshing the page or
								contacting support if the problem persists.
							</p>
						</div>
					)}
				</div>
				<p className="text-gray-600 text-xs mt-8">
					Legacy Knowledge Graph and Short-Term Memory systems have
					been deprecated in favor of the unified Supermemory
					integration.
				</p>
			</div>
		</div>
	)
}

export default Memories
