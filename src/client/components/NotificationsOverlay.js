"use client"

import React, { useState, useEffect, useCallback } from "react"
import toast from "react-hot-toast"
import { Tooltip } from "react-tooltip"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import {
	IconLoader,
	IconBell,
	IconAlertCircle,
	IconArrowRight,
	IconX
} from "@tabler/icons-react"

const NotificationsOverlay = ({ onClose }) => {
	const [notifications, setNotifications] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [error, setError] = useState(null)
	const router = useRouter()

	const fetchNotifications = useCallback(async () => {
		setIsLoading(true)
		setError(null)
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
				const sortedNotifications = data.notifications.sort(
					(a, b) =>
						new Date(b.timestamp).getTime() -
						new Date(a.timestamp).getTime()
				)
				setNotifications(sortedNotifications)
			} else {
				throw new Error("Invalid notification data format")
			}
		} catch (error) {
			const errorMsg = `Error fetching notifications: ${error.message}`
			toast.error(errorMsg)
			setError(errorMsg)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchNotifications()
	}, [fetchNotifications])

	const formatTimestamp = (timestamp) => {
		if (!timestamp) return "No timestamp"
		try {
			return new Date(timestamp).toLocaleString(undefined, {
				dateStyle: "medium",
				timeStyle: "short"
			})
		} catch (e) {
			return timestamp
		}
	}

	const handleDelete = async (e, notificationId) => {
		e.stopPropagation()
		const originalNotifications = [...notifications]
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
			setNotifications(originalNotifications)
		}
	}

	const handleNotificationClick = (e, notif) => {
		e.stopPropagation()
		// A notification is associated with a task, but the user may not want to navigate away.
		// We'll just close the overlay for now. A future enhancement could be a "View Task" button.
		if (notif.task_id) {
			router.push("/tasks")
		}
		onClose()
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
			onClick={onClose}
		>
			<Tooltip id="notifications-overlay-tooltip" />
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-lg border border-[var(--color-primary-surface-elevated)] max-h-[70vh] flex flex-col"
			>
				<header className="flex justify-between items-center mb-6 flex-shrink-0">
					<h2 className="text-xl font-semibold text-white flex items-center gap-3">
						<IconBell /> Notifications
					</h2>
					<button
						onClick={onClose}
						className="p-1 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
					>
						<IconX size={20} />
					</button>
				</header>
				<main className="flex-1 w-full flex flex-col overflow-hidden">
					{isLoading ? (
						<div className="flex-grow flex flex-col justify-center items-center text-center p-4">
							<IconLoader className="w-8 h-8 text-[var(--color-accent-blue)] animate-spin" />
							<span className="ml-3 text-[var(--color-text-secondary)] mt-2">
								Loading...
							</span>
						</div>
					) : error ? (
						<div className="flex-grow flex flex-col justify-center items-center text-center p-4">
							<IconAlertCircle className="w-10 h-10 text-[var(--color-accent-red)] mb-3" />
							<p className="text-[var(--color-accent-red)]">
								Could not load notifications
							</p>
							<p className="text-[var(--color-text-muted)] text-sm mt-1">
								{error}
							</p>
						</div>
					) : notifications.length === 0 ? (
						<div className="flex-grow flex flex-col justify-center items-center text-center p-4">
							<IconBell className="w-12 h-12 text-[var(--color-text-muted)] mb-3" />
							<p className="text-[var(--color-text-secondary)]">
								No new notifications
							</p>
						</div>
					) : (
						<div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
							{notifications.map((notif) => (
								<div
									key={notif.id ?? Math.random()}
									onClick={(e) =>
										handleNotificationClick(e, notif)
									}
									className="flex items-center gap-4 bg-[var(--color-primary-surface)] p-3 rounded-lg border border-[var(--color-primary-surface-elevated)]/50 shadow-sm cursor-pointer hover:bg-[var(--color-primary-surface-elevated)]/70 transition-colors group"
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
											className="p-1.5 text-[var(--color-text-muted)] rounded-full opacity-0 group-hover:opacity-100 hover:bg-[var(--color-primary-surface-elevated)] hover:text-[var(--color-accent-red)] transition-all"
											data-tooltip-id="notifications-overlay-tooltip"
											data-tooltip-content="Dismiss"
										>
											<IconX size={16} />
										</button>
										{notif.task_id && (
											<IconArrowRight
												className="w-5 h-5 text-[var(--color-text-muted)] transition-transform group-hover:translate-x-1"
												data-tooltip-id="notifications-overlay-tooltip"
												data-tooltip-content="View Task"
											/>
										)}
									</div>
								</div>
							))}
						</div>
					)}
				</main>
			</motion.div>
		</motion.div>
	)
}

export default NotificationsOverlay
