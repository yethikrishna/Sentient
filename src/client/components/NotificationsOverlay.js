"use client"

import React, { useState, useEffect, useCallback } from "react" // eslint-disable-line
import toast from "react-hot-toast"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import {
	IconLoader,
	IconBell,
	IconAlertCircle,
	IconX,
	IconArrowRight
} from "@tabler/icons-react"
import { formatDistanceToNow, parseISO } from "date-fns"

const NotificationItem = ({
	notification,
	onDelete,
	onClick,
	userTimezone
}) => {
	let formattedTimestamp = "..." // Placeholder while timezone is loading

	try {
		const date = parseISO(notification.timestamp)
		if (typeof userTimezone === "string") {
			// If timezone is available, format to an absolute time string
			formattedTimestamp = new Intl.DateTimeFormat(undefined, {
				month: "short",
				day: "numeric",
				hour: "numeric",
				minute: "2-digit",
				hour12: true,
				timeZone: userTimezone
			}).format(date)
		} else if (userTimezone === null) {
			// Fallback to relative time if timezone fetch completes but is not set
			formattedTimestamp = formatDistanceToNow(date, { addSuffix: true })
		}
	} catch (e) {
		formattedTimestamp = "Recently" // Fallback for invalid date
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, x: -20 }}
			onClick={() => onClick(notification)}
			className="flex items-center gap-4 bg-neutral-800/50 p-3 rounded-lg border border-neutral-700/50 shadow-sm cursor-pointer hover:bg-neutral-700/70 transition-colors group"
		>
			<div className="flex-shrink-0 pt-1 self-start">
				<IconBell className="w-5 h-5 text-[var(--color-accent-blue)]" />
			</div>
			<div className="flex-grow">
				<p className="text-neutral-100 text-sm leading-relaxed mb-1">
					{notification.message || "No message content."}
				</p>
				<p className="text-neutral-400 text-xs">{formattedTimestamp}</p>
			</div>
			<div className="flex items-center gap-1 flex-shrink-0 self-start">
				<button
					onClick={(e) => {
						e.stopPropagation()
						onDelete(notification.id)
					}}
					className="p-1.5 text-neutral-500 rounded-full opacity-0 group-hover:opacity-100 hover:bg-neutral-600 hover:text-red-400 transition-all"
				>
					<IconX size={14} />
				</button>
				{notification.task_id && (
					<IconArrowRight className="w-5 h-5 text-neutral-500 transition-transform group-hover:translate-x-0.5" />
				)}
			</div>
		</motion.div>
	)
}

const NotificationsOverlay = ({ onClose }) => {
	const [notifications, setNotifications] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [error, setError] = useState(null)
	const [userTimezone, setUserTimezone] = useState(undefined) // undefined: loading, null: not found, string: found
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
		} catch (err) {
			const errorMsg = `Error fetching notifications: ${err.message}`
			toast.error(errorMsg)
			setError(errorMsg)
		} finally {
			setIsLoading(false)
		}
	}, [])

	const fetchUserData = useCallback(async () => {
		try {
			const response = await fetch("/api/user/data")
			if (!response.ok) {
				throw new Error("Failed to fetch user data")
			}
			const result = await response.json()
			const timezone = result?.data?.personalInfo?.timezone
			setUserTimezone(timezone || null) // Set to null if not found
		} catch (err) {
			console.error(
				"NotificationsOverlay: Failed to fetch user timezone",
				err
			)
			setUserTimezone(null) // Set to null on error to trigger fallback
		}
	}, [])

	useEffect(() => {
		fetchNotifications()
		fetchUserData()
	}, [fetchNotifications, fetchUserData])

	const handleDelete = async (e, notificationId) => {
		if (e && e.stopPropagation) e.stopPropagation()
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
		} catch (err) {
			toast.error(`Error dismissing notification: ${err.message}`)
			setNotifications(originalNotifications)
		}
	}

	const handleNotificationClick = (e, notif) => {
		if (e && e.stopPropagation) e.stopPropagation()
		// A notification is associated with a task, but the user may not want to navigate away.
		// We'll just close the overlay for now. A future enhancement could be a "View Task" button.
		if (notif.task_id) {
			router.push(`/tasks?taskId=${notif.task_id}`)
		}
		onClose()
	}

	const handleClearAll = async () => {
		if (
			!window.confirm(
				"Are you sure you want to dismiss all notifications?"
			)
		)
			return
		const originalNotifications = [...notifications]
		setNotifications([])

		const deletionPromises = originalNotifications.map((n) =>
			handleDelete(null, n.id)
		)

		try {
			await Promise.all(deletionPromises)
			toast.success("All notifications dismissed.")
		} catch (err) {
			toast.error(`Could not dismiss all notifications: ${err.message}`)
			setNotifications(originalNotifications)
		}
	}

	const overlayVariants = {
		hidden: { opacity: 0, y: 20, scale: 0.95 },
		visible: { opacity: 1, y: 0, scale: 1 },
		exit: { opacity: 0, y: 20, scale: 0.95 }
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
			onClick={onClose}
		>
			<motion.div
				variants={overlayVariants}
				initial="hidden"
				animate="visible"
				exit="exit"
				transition={{ duration: 0.2, ease: "easeInOut" }}
				onClick={(e) => e.stopPropagation()}
				className="absolute bottom-[90px] right-6 bg-neutral-900/90 backdrop-blur-xl p-4 rounded-2xl shadow-2xl w-full max-w-md border border-neutral-700 max-h-[70vh] flex flex-col"
			>
				<header className="flex justify-between items-center mb-4 flex-shrink-0">
					<h2 className="text-lg font-semibold text-white flex items-center gap-2">
						<IconBell /> Notifications
					</h2>
					<button
						onClick={onClose}
						className="p-1.5 rounded-full hover:bg-neutral-700"
					>
						<IconX size={18} />
					</button>
				</header>
				<main className="flex-1 w-full flex flex-col overflow-hidden">
					{isLoading ? (
						<div className="flex-grow flex flex-col justify-center items-center text-center p-4">
							<IconLoader className="w-8 h-8 text-[var(--color-accent-blue)] animate-spin" />
							<span className="text-neutral-400 mt-2">
								Loading...
							</span>
						</div>
					) : error ? (
						<div className="flex-grow flex flex-col justify-center items-center text-center p-4">
							<IconAlertCircle className="w-10 h-10 text-red-500 mb-3" />
							<p className="text-red-400">
								Could not load notifications
							</p>
							<p className="text-neutral-500 text-sm mt-1">
								{error}
							</p>
						</div>
					) : notifications.length === 0 ? (
						<div className="flex-grow flex flex-col justify-center items-center text-center p-4">
							<IconBell className="w-12 h-12 text-neutral-600 mb-3" />
							<p className="text-neutral-400">All caught up!</p>
							<p className="text-neutral-500 text-sm">
								You have no new notifications.
							</p>
						</div>
					) : (
						<div className="flex-1 overflow-y-auto space-y-3 pr-1 custom-scrollbar">
							{notifications.map((notif) => (
								<NotificationItem
									key={notif.id}
									notification={notif}
									userTimezone={userTimezone}
									onDelete={(id) => handleDelete(null, id)}
									onClick={(n) =>
										handleNotificationClick(null, n)
									}
								/>
							))}
						</div>
					)}
				</main>
				{notifications.length > 0 && !isLoading && (
					<footer className="mt-4 pt-3 border-t border-neutral-800 flex-shrink-0">
						<button
							onClick={handleClearAll}
							className="w-full text-center text-sm text-neutral-400 hover:text-white hover:bg-neutral-700/50 py-2 rounded-lg transition-colors"
						>
							Dismiss All
						</button>
					</footer>
				)}
			</motion.div>
		</motion.div>
	)
}

export default NotificationsOverlay
