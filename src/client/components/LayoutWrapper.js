"use client"
import React, { useState, useEffect, useCallback, useRef } from "react"
import { usePathname, useRouter } from "next/navigation"
import { AnimatePresence, motion } from "framer-motion"
import NotificationsOverlay from "@components/NotificationsOverlay"
import { IconBell } from "@tabler/icons-react"
import FloatingNav from "@components/FloatingNav"
import CommandPalette from "./CommandPallete"
import { useGlobalShortcuts } from "@hooks/useGlobalShortcuts"

export default function LayoutWrapper({ children }) {
	const [isNotificationsOpen, setNotificationsOpen] = useState(false)
	const [isCommandPaletteOpen, setCommandPaletteOpen] = useState(false)
	const [unreadCount, setUnreadCount] = useState(0)
	const [userDetails, setUserDetails] = useState(null)
	const wsRef = useRef(null)
	const pathname = usePathname()

	const showNav = !["/", "/onboarding"].includes(pathname)

	useEffect(() => {
		fetch("/api/user/profile")
			.then((res) => (res.ok ? res.json() : null))
			.then((data) => setUserDetails(data))
	}, [])

	useEffect(() => {
		if (!userDetails?.sub) return

		const connectWebSocket = async () => {
			if (wsRef.current && wsRef.current.readyState < 2) return

			try {
				const tokenResponse = await fetch("/api/auth/token")
				if (!tokenResponse.ok) {
					setTimeout(connectWebSocket, 5000)
					return
				}
				const { accessToken } = await tokenResponse.json()
				const wsProtocol =
					window.location.protocol === "https:" ? "wss" : "ws"
				const serverUrlHttp =
					process.env.NEXT_PUBLIC_APP_SERVER_URL ||
					"http://localhost:5000"
				const serverHost = serverUrlHttp.replace(/^https?:\/\//, "")
				const wsUrl = `${wsProtocol}://${serverHost}/api/ws/notifications`

				const ws = new WebSocket(wsUrl)
				ws.isCleaningUp = false
				wsRef.current = ws

				ws.onopen = () =>
					ws.send(
						JSON.stringify({ type: "auth", token: accessToken })
					)
				ws.onmessage = (event) => {
					const data = JSON.parse(event.data)
          if (data.type === "task_progress_update") {
						// Dispatch a custom event that the tasks page can listen for
						window.dispatchEvent(
							new CustomEvent("taskProgressUpdate", {
								detail: data.payload
							})
						)
					} else if (data.type === "task_list_updated") {
						// This is a generic event telling the app that tasks have changed
						// on the backend and the UI should refetch them.
						window.dispatchEvent(
							new CustomEvent("tasksUpdatedFromBackend")
						)
					}
				}
				ws.onclose = () => {
					if (!ws.isCleaningUp) {
						wsRef.current = null
						setTimeout(connectWebSocket, 5000)
					}
				}
				ws.onerror = () => ws.close()
			} catch (error) {
				setTimeout(connectWebSocket, 5000)
			}
		}
		connectWebSocket()

		return () => {
			if (wsRef.current) {
				wsRef.current.isCleaningUp = true
				wsRef.current.close()
				wsRef.current = null
			}
		}
	}, [userDetails?.sub])

	const handleNotificationsOpen = useCallback(() => {
		setNotificationsOpen(true)
		setUnreadCount(0)
	}, [])

	// Use the new custom hook for shortcuts
	useGlobalShortcuts(
		handleNotificationsOpen,
		() => setCommandPaletteOpen((prev) => !prev)
	)

	useEffect(() => {
		const handleEscape = (e) => {
			if (e.key === "Escape") {
				if (isNotificationsOpen) setNotificationsOpen(false)
				if (isCommandPaletteOpen) setCommandPaletteOpen(false)
			}
		}
		window.addEventListener("keydown", handleEscape)
		return () => window.removeEventListener("keydown", handleEscape)
	}, [isNotificationsOpen, isCommandPaletteOpen])

	return (
		<>
			{showNav && <FloatingNav />}
			{showNav && (
				<CommandPalette
					open={isCommandPaletteOpen}
					setOpen={setCommandPaletteOpen}
				/>
			)}
			{children}
			{showNav && (
				<>
					<button
						onClick={handleNotificationsOpen}
						className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-800/80 backdrop-blur-md border border-neutral-700 shadow-lg hover:bg-neutral-700 transition-colors"
						aria-label="Open notifications"
					>
						<IconBell className="h-7 w-7 text-neutral-200" />
						{unreadCount > 0 && (
							<motion.div
								initial={{ scale: 0 }}
								animate={{ scale: 1 }}
								className="absolute top-1 right-1 h-3 w-3 bg-red-500 rounded-full border-2 border-neutral-800"
							/>
						)}
					</button>
					<AnimatePresence>
						{isNotificationsOpen && (
							<NotificationsOverlay
								onClose={() => setNotificationsOpen(false)}
							/>
						)}
					</AnimatePresence>
				</>
			)}
		</>
	)
}
