// src/client/app/notifications/page.js
"use client"
import React, { useState, useEffect, useCallback } from "react"
import {
	IconLoader,
	IconBell,
	IconAlertCircle,
	IconArrowRight,
	IconX,
	IconMenu2
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import Sidebar from "@components/Sidebar"
import { cn } from "@utils/cn"
import { useRouter } from "next/navigation"

const Notifications = () => {
	const [notifications, setNotifications] = useState([])
	const [isLoading, setIsLoading] = useState(true) // Start loading initially
	const [userDetails, setUserDetails] = useState({}) // Initialize to empty object
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [error, setError] = useState(null) // State for storing fetch errors
	const router = useRouter()

	const fetchNotifications = useCallback(async () => {
		console.log("Fetching notifications...")
		setIsLoading(true)
		setError(null) // Clear previous errors
		try {
			const response = await fetch("/api/notifications")

			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(
					errorData.error ||
						`Server responded with ${response.status}`
				)
			}

			const data = await response.json()
			if (Array.isArray(data.notifications)) {
				// Sort notifications by timestamp, newest first
				const sortedNotifications = data.notifications.sort((a, b) => {
					try {
						return (
							new Date(b.timestamp).getTime() -
							new Date(a.timestamp).getTime()
						)
					} catch {
						return 0
					} // Keep order if dates invalid
				})
				setNotifications(sortedNotifications)
				console.log(
					"Notifications fetched:",
					sortedNotifications.length
				)
			} else {
				throw new Error("Invalid notification data format")
			}
		} catch (error) {
			// Handle network or other exceptions during fetch
			console.error("Catch Error fetching notifications:", error)
			const errorMsg = `Error fetching notifications: ${error.message}`
			toast.error(errorMsg)
			setNotifications([])
			setError(errorMsg)
		} finally {
			setIsLoading(false) // Always set loading to false after fetch attempt
		}
	}, [])

	// Function to fetch user details
	const fetchUserDetails = async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) {
				throw new Error("Failed to fetch user profile")
			}
			const data = await response.json()
			setUserDetails(data || {})
		} catch (error) {
			toast.error("Error fetching user details for sidebar.")
			console.error("Error fetching user details for sidebar:", error)
			setUserDetails({})
		}
	}

	useEffect(() => {
		fetchUserDetails()
		fetchNotifications() // Call fetch on initial mount

		const intervalId = setInterval(fetchNotifications, 120000) // Refresh every 2 minutes
		return () => clearInterval(intervalId) // Cleanup interval on unmount
	}, [fetchNotifications]) // Dependency array correctly contains fetchNotifications

	// Helper function to format timestamp
	const formatTimestamp = (timestamp) => {
		if (!timestamp) return "No timestamp"
		try {
			return new Date(timestamp).toLocaleString(undefined, {
				dateStyle: "medium",
				timeStyle: "short"
			})
		} catch (e) {
			console.warn("Error formatting timestamp:", timestamp, e)
			return timestamp
		}
	}

	const handleDelete = async (e, notificationId) => {
		e.stopPropagation() // Prevent card's onClick from firing

		const originalNotifications = [...notifications]
		// Optimistically update UI
		setNotifications(notifications.filter((n) => n.id !== notificationId))

		try {
			const response = await fetch("/api/notifications/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ notification_id: notificationId })
			})

			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(
					errorData.error || "Failed to delete notification"
				)
			}
			toast.success("Notification dismissed.")
		} catch (error) {
			toast.error(`Error dismissing notification: ${error.message}`)
			// Revert UI on failure
			setNotifications(originalNotifications)
		}
	}

	// --- Render Logic ---
	return (
		<div className="flex h-screen bg-matteblack dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>

			<div className="flex-1 flex flex-col overflow-hidden">
				<header className="flex items-center justify-between p-4 bg-matteblack border-b border-neutral-800 md:flex-row md:items-center">
					<button
						onClick={() => setSidebarVisible(true)}
						className="text-white md:hidden"
					>
						<IconMenu2 />
					</button>
					<h1 className="text-2xl sm:text-3xl font-light text-white flex-grow text-center md:text-left md:flex-grow-0">
						Notifications
					</h1>
				</header>

				<main className="flex-1 w-full max-w-3xl mx-auto flex flex-col overflow-hidden p-4 sm:p-6">
					{isLoading ? ( // Handle loading state first
						<div className="flex-grow flex flex-col justify-center items-center text-center p-10">
							<IconLoader className="w-10 h-10 text-lightblue animate-spin" />
							<span className="ml-3 text-gray-400 text-lg mt-4">
								Loading Notifications...
							</span>
						</div>
					) : error ? ( // Display error message if error state is set
						<div className="flex-grow flex flex-col justify-center items-center text-center p-10">
							<IconAlertCircle className="w-12 h-12 text-red-500 mb-4" />
							<p className="text-red-400 text-lg mb-4">
								Could not load notifications
							</p>
							<p className="text-gray-500 text-sm mb-6">
								{error}
							</p>
							<button
								onClick={fetchNotifications} // Allow retry
								className="py-2 px-5 rounded bg-lightblue hover:bg-blue-700 text-white text-sm font-medium transition-colors"
							>
								Retry
							</button>
						</div>
					) : notifications.length === 0 ? ( // Display empty state if no error and not loading
						<div className="flex-grow flex flex-col justify-center items-center text-center p-10">
							<IconBell className="w-16 h-16 text-neutral-700 mb-4" />
							<p className="text-gray-500 text-xl">
								No new notifications
							</p>
							<p className="text-gray-600 text-sm mt-2">
								Check back later for updates.
							</p>
						</div>
					) : (
						// Display notification list
						<div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
							{notifications.map((notif) => (
								<div // eslint-disable-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
									key={notif.id ?? Math.random()}
									onClick={() => router.push("/tasks")}
									className="flex items-center gap-4 bg-neutral-800 p-4 rounded-lg border border-neutral-700/50 shadow-sm cursor-pointer hover:bg-neutral-700/70 transition-colors group"
								>
									<div className="flex-shrink-0 pt-1">
										<IconBell className="w-5 h-5 text-lightblue" />
									</div>
									<div className="flex-grow">
										<p className="text-white text-sm leading-relaxed mb-1">
											{notif.message ||
												"No message content."}
										</p>
										<p className="text-gray-500 text-xs">
											{formatTimestamp(notif.timestamp)}
										</p>
									</div>
									<div className="flex items-center gap-2 flex-shrink-0">
										<button
											onClick={(e) =>
												handleDelete(e, notif.id)
											}
											className="p-1.5 text-gray-500 rounded-full opacity-0 group-hover:opacity-100 hover:bg-neutral-600 hover:text-red-400 transition-all duration-200"
											title="Dismiss notification"
										>
											<IconX size={16} />
										</button>
										<IconArrowRight className="w-5 h-5 text-gray-500 transition-transform duration-300 group-hover:translate-x-1 group-hover:text-white" />
									</div>
								</div>
							))}
						</div>
					)}
				</main>
			</div>
		</div>
	)
}

export default Notifications
