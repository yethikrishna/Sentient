"use client"
import React, { useState, useEffect, useCallback, useRef } from "react"
import { usePathname, useRouter } from "next/navigation"
import { AnimatePresence, motion } from "framer-motion"
import NotificationsOverlay from "@components/NotificationsOverlay"
import { IconBell } from "@tabler/icons-react"
import Sidebar from "@components/Sidebar"
import CommandPalette from "./CommandPallete" // Corrected import path
import { useGlobalShortcuts } from "@hooks/useGlobalShortcuts"
import { cn } from "@utils/cn"

export default function LayoutWrapper({ children }) {
	const [isNotificationsOpen, setNotificationsOpen] = useState(false)
	const [isCommandPaletteOpen, setCommandPaletteOpen] = useState(false)
	const [isSidebarCollapsed, setSidebarCollapsed] = useState(true)
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
	useGlobalShortcuts(handleNotificationsOpen, () =>
		setCommandPaletteOpen((prev) => !prev)
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
			{showNav && (
				<Sidebar
					isCollapsed={isSidebarCollapsed}
					onToggle={() => setSidebarCollapsed(!isSidebarCollapsed)}
					onNotificationsOpen={handleNotificationsOpen}
					unreadCount={unreadCount}
				/>
			)}
			{showNav && (
				<CommandPalette
					open={isCommandPaletteOpen}
					setOpen={setCommandPaletteOpen}
				/>
			)}
			<div
				className={cn(
					"flex-1 transition-[padding-left] duration-300 ease-in-out",
					showNav &&
						(isSidebarCollapsed ? "md:pl-20" : "md:pl-[260px]")
				)}
			>
				{children}
			</div>
			<AnimatePresence>
				{isNotificationsOpen && (
					<NotificationsOverlay
						onClose={() => setNotificationsOpen(false)}
					/>
				)}
			</AnimatePresence>
		</>
	)
}
