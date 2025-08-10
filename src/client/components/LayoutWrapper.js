// src/client/components/LayoutWrapper.js
"use client"
import React, { useState, useEffect, useCallback, useRef, createContext } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation" // Import useSearchParams
import { AnimatePresence } from "framer-motion"
import NotificationsOverlay from "@components/NotificationsOverlay"
import { IconMenu2, IconLoader } from "@tabler/icons-react"
import Sidebar from "@components/Sidebar"
import CommandPalette from "./CommandPallete"
import GlobalSearch from "./GlobalSearch"
import { useGlobalShortcuts } from "@hooks/useGlobalShortcuts"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"
import { useUser } from "@auth0/nextjs-auth0/client"

export const PlanContext = createContext({
	plan: "free",
	isPro: false,
	isLoading: true
})

export default function LayoutWrapper({ children }) {
	const [isNotificationsOpen, setNotificationsOpen] = useState(false)
	const [isSearchOpen, setSearchOpen] = useState(false)
	const [isCommandPaletteOpen, setCommandPaletteOpen] = useState(false)
	const [isSidebarCollapsed, setSidebarCollapsed] = useState(true)
	const [isMobileNavOpen, setMobileNavOpen] = useState(false)
	const [unreadCount, setUnreadCount] = useState(0)
	const wsRef = useRef(null)
	const pathname = usePathname()
	const router = useRouter()
	const searchParams = useSearchParams() // Hook to read URL query parameters

	const { user, error: authError, isLoading: isAuthLoading } = useUser()

	const [isLoading, setIsLoading] = useState(true)
	const [isAllowed, setIsAllowed] = useState(false)

	const showNav = !["/", "/onboarding"].includes(pathname)

	// **NEW EFFECT**: Handles programmatic session refresh after payment
	useEffect(() => {
		const paymentStatus = searchParams.get("payment_status")
		if (paymentStatus === "success") {
			const refreshSession = async () => {
				toast.loading(
					"Payment successful! Refreshing your session...",
					{ duration: 4000 }
				)
				try {
					// Calling this endpoint refreshes the session cookie with new data (like the "Pro" role)
					await fetch("/api/auth/me")
					// Clean the URL by removing the query parameter, then reload the page
					router.replace(pathname, { scroll: false })
					window.location.reload()
				} catch (error) {
					toast.error(
						"Failed to refresh session. Please log in again to see your new plan."
					)
				}
			}
			refreshSession()
		}
	}, [searchParams, router, pathname])

	useEffect(() => {
		if (!showNav) {
			setIsLoading(false)
			setIsAllowed(true)
			return
		}

		if (isAuthLoading) return

		if (authError) {
			toast.error("Session error. Redirecting to login.")
			router.push("/api/auth/login")
			return
		}

		if (!user) {
			router.push("/api/auth/login")
			return
		}

		const checkStatus = async () => {
			setIsLoading(true)
			try {
				const res = await fetch("/api/user/data")
				if (!res.ok) throw new Error("Could not verify user status.")
				const data = await res.json()
				if (data?.data?.onboardingComplete) {
					setIsAllowed(true)
				} else {
					toast.error("Please complete onboarding first.")
					router.push("/onboarding")
				}
			} catch (error) {
				toast.error(error.message)
				router.push("/")
			} finally {
				setIsLoading(false)
			}
		}

		checkStatus()
	}, [pathname, router, showNav, user, authError, isAuthLoading])

	// ... (keep the rest of the useEffects and functions exactly as they were)
	useEffect(() => {
		if (!user?.sub) return

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
						window.dispatchEvent(
							new CustomEvent("taskProgressUpdate", {
								detail: data.payload
							})
						)
					} else if (data.type === "task_list_updated") {
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
	}, [user?.sub])

	const handleNotificationsOpen = useCallback(() => {
		setNotificationsOpen(true)
		setUnreadCount(0)
	}, [])

	useGlobalShortcuts(handleNotificationsOpen, () =>
		setCommandPaletteOpen((prev) => !prev)
	)

	if (isLoading || isAuthLoading) {
		return (
			<div className="flex-1 flex h-screen bg-black text-white overflow-hidden justify-center items-center">
				<IconLoader className="w-10 h-10 animate-spin text-brand-orange" />
			</div>
		)
	}

	if (!isAllowed) {
		return (
			<div className="flex-1 flex h-screen bg-black text-white overflow-hidden justify-center items-center">
				<IconLoader className="w-10 h-10 animate-spin text-brand-orange" />
			</div>
		)
	}
	return (
		<PlanContext.Provider
			value={{
				plan: (user?.[`${process.env.NEXT_PUBLIC_AUTH0_NAMESPACE}/roles`] || []).includes("Pro") ? "pro" : "free",
				isPro: (user?.[`${process.env.NEXT_PUBLIC_AUTH0_NAMESPACE}/roles`] || []).includes("Pro"),
				isLoading: isAuthLoading
			}}
		>
			{showNav && (
				<>
					<Sidebar
						isCollapsed={isSidebarCollapsed}
						onToggle={() =>
							setSidebarCollapsed(!isSidebarCollapsed)
						}
						onNotificationsOpen={handleNotificationsOpen}
						onSearchOpen={() => setSearchOpen(true)}
						unreadCount={unreadCount}
						isMobileOpen={isMobileNavOpen}
						onMobileClose={() => setMobileNavOpen(false)}
						user={user}
					/>
					<button
						onClick={() => setMobileNavOpen(true)}
						className="md:hidden fixed top-4 left-4 z-30 p-2 rounded-full bg-neutral-800/50 backdrop-blur-sm text-white"
					>
						<IconMenu2 size={20} />
					</button>
				</>
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
			<AnimatePresence>
				{isSearchOpen && (
					<GlobalSearch onClose={() => setSearchOpen(false)} />
				)}
			</AnimatePresence>
		</PlanContext.Provider>
	)
}
