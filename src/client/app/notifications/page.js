"use client"
import React, { useState, useEffect, useCallback, useRef } from "react"
import {
	IconLoader,
	IconBell,
	IconAlertCircle,
	IconArrowRight,
	IconHelpCircle,
	IconX
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"
import { useRouter } from "next/navigation"

const HelpTooltip = ({ content }) => (
	<div className="absolute top-6 right-6 z-40">
		<button
			data-tooltip-id="page-help-tooltip"
			data-tooltip-content={content}
			className="p-1.5 rounded-full text-neutral-500 hover:text-white hover:bg-[var(--color-primary-surface)] pulse-glow-animation"
		>
			<IconHelpCircle size={22} />
		</button>
	</div>
)

const Notifications = () => {
	const [notifications, setNotifications] = useState([])
	const [isLoading, setIsLoading] = useState(true) // Start loading initially
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

	useEffect(() => {
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
		<div className="flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] overflow-x-hidden pl-0 md:pl-20">
			<Tooltip id="notifications-tooltip" />
			<Tooltip id="page-help-tooltip" />
			<div className="flex-1 flex flex-col overflow-hidden relative">
				<header className="flex items-center justify-between p-4 md:px-8 md:py-6 bg-[var(--color-primary-background)] border-b border-[var(--color-primary-surface)]">
					<HelpTooltip content="This page shows notifications from Sentient, such as when a task is ready for approval or has completed." />
					<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)] flex items-center gap-3">
						Notifications
					</h1>
				</header>

				<main className="flex-1 w-full max-w-3xl mx-auto flex flex-col overflow-hidden p-4 sm:p-6">
					{isLoading ? ( // Handle loading state first
						<div className="flex-grow flex flex-col justify-center items-center text-center p-10">
							<IconLoader className="w-10 h-10 text-[var(--color-accent-blue)] animate-spin" />
							<span className="ml-3 text-[var(--color-text-secondary)] text-lg mt-4">
								Loading Notifications...
							</span>
						</div>
					) : error ? ( // Display error message if error state is set
						<div className="flex-grow flex flex-col justify-center items-center text-center p-10">
							<IconAlertCircle className="w-12 h-12 text-[var(--color-accent-red)] mb-4" />
							<p className="text-[var(--color-accent-red)] text-lg mb-4">
								Could not load notifications
							</p>
							<p className="text-[var(--color-text-muted)] text-sm mb-6">
								{error}
							</p>
							<button
								onClick={fetchNotifications} // Allow retry
								className="py-2 px-5 rounded-lg bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white text-sm font-medium transition-colors"
							>
								Retry
							</button>
						</div>
					) : notifications.length === 0 ? ( // Display empty state if no error and not loading
						<div className="flex-grow flex flex-col justify-center items-center text-center p-10">
							<IconBell className="w-16 h-16 text-[var(--color-text-muted)] mb-4" />
							<p className="text-[var(--color-text-secondary)] text-xl">
								No new notifications
							</p>
							<p className="text-[var(--color-text-muted)] text-sm mt-2">
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
									className="flex items-center gap-4 bg-[var(--color-primary-surface)] p-4 rounded-lg border border-[var(--color-primary-surface-elevated)]/50 shadow-sm cursor-pointer hover:bg-[var(--color-primary-surface-elevated)]/70 transition-colors group"
								>
									<div className="flex-shrink-0 pt-1">
										<IconBell className="w-5 h-5 text-[var(--color-accent-blue)]" />
									</div>
									<div className="flex-grow">
										<p className="text-[var(--color-text-primary)] text-sm leading-relaxed mb-1">
											{notif.message ||
												"No message content."}
										</p>
										<p className="text-[var(--color-text-muted)] text-xs">
											{formatTimestamp(notif.timestamp)}
										</p>
									</div>
									<div className="flex items-center gap-2 flex-shrink-0">
										<button
											onClick={(e) =>
												handleDelete(e, notif.id)
											}
											className="p-1.5 text-[var(--color-text-muted)] rounded-full opacity-0 group-hover:opacity-100 hover:bg-[var(--color-primary-surface-elevated)] hover:text-[var(--color-accent-red)] transition-all duration-200"
											data-tooltip-id="notifications-tooltip"
											data-tooltip-content="Dismiss notification"
										>
											<IconX size={16} />
										</button>
										<IconArrowRight
											className="w-5 h-5 text-[var(--color-text-muted)] transition-transform duration-300 group-hover:translate-x-1 group-hover:text-white"
											data-tooltip-id="notifications-tooltip"
											data-tooltip-content="View associated tasks"
										/>
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
