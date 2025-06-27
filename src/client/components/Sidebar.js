"use client"
import { useRouter, usePathname } from "next/navigation"
import { useEffect, useState, useRef, useCallback } from "react"
import {
	IconAdjustments,
	IconBell,
	IconBook,
	IconChecklist,
	IconChevronDown,
	IconHome,
	IconLogout,
	IconPlus,
	IconSearch,
	IconUser,
	IconX
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { AnimatePresence, motion } from "framer-motion"
import { cn } from "@utils/cn"

const Sidebar = ({ userDetails, setSidebarVisible, isSidebarVisible }) => {
	const router = useRouter()
	const [pricing, setPricing] = useState("free")
	const wsRef = useRef(null)
	// Removed chat list state and handlers

	const fetchPricingPlan = useCallback(async () => {
		try {
			const response = await fetch("/api/user/pricing")
			if (!response.ok) throw new Error("Failed to fetch")
			const data = await response.json()
			setPricing(data.pricing || "free")
		} catch (error) {
			toast.error("Error fetching pricing plan.")
		}
	}, [])

	const logout = () => {
		router.push("/auth/logout")
	}

	// Removed chat-related handlers: fetchChats, handleRenameChat, handleDeleteChat

	// Separate effect for fetching data, depends on userDetails
	useEffect(() => {
		if (!userDetails) {
			return
		}
		fetchPricingPlan()
	}, [userDetails, fetchPricingPlan])

	// Separate, dedicated effect for WebSocket lifecycle management
	useEffect(() => {
		// Guard clause: Do not run WebSocket logic if userDetails.sub is not yet available.
		if (!userDetails?.sub) {
			return
		}

		const connectWebSocket = async () => {
			if (wsRef.current && wsRef.current.readyState < 2) {
				// 0=CONNECTING, 1=OPEN
				console.log(
					"Sidebar WS: A connection is already open or connecting."
				)
				return
			}

			try {
				const tokenResponse = await fetch("/api/auth/token")
				if (!tokenResponse.ok) {
					console.error(
						"Sidebar WS: Could not get auth token for WebSocket."
					)
					// Retry after a delay if token fetch fails
					setTimeout(connectWebSocket, 5000)
					return
				}
				const { accessToken } = await tokenResponse.json()

				const wsProtocol =
					window.location.protocol === "https:" ? "wss" : "ws"
				const serverUrlHttp =
					process.env.NEXT_PUBLIC_APP_SERVER_URL ||
					"http://localhost:5000"
				const serverUrlWs = serverUrlHttp.replace(/^http/, "ws")
				const wsUrl = `${serverUrlWs}/api/ws/notifications`

				const ws = new WebSocket(wsUrl)
				ws.isCleaningUp = false // Custom flag on the instance itself
				wsRef.current = ws

				ws.onopen = () => {
					console.log("Sidebar: Notification WebSocket connected.")
					ws.send(
						JSON.stringify({ type: "auth", token: accessToken })
					)
				}

				ws.onmessage = (event) => {
					const data = JSON.parse(event.data)
					if (data.type === "new_notification" && data.notification) {
						toast.custom(
							(t) => (
								<div
									className={`${t.visible ? "animate-enter" : "animate-leave"} max-w-md w-full bg-neutral-800 shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 border border-neutral-700`}
								>
									<div className="flex-1 w-0 p-4">
										<div className="flex items-start">
											<div className="flex-shrink-0 pt-0.5">
												<IconBell className="h-6 w-6 text-lightblue" />
											</div>
											<div className="ml-3 flex-1">
												<p className="text-sm font-medium text-white">
													New Notification
												</p>
												<p className="mt-1 text-sm text-gray-400">
													{data.notification.message}
												</p>
											</div>
										</div>
									</div>
									<div className="flex border-l border-neutral-700">
										<button
											onClick={() => {
												router.push("/tasks")
												toast.dismiss(t.id)
											}}
											className="w-full border border-transparent rounded-none rounded-r-lg p-4 flex items-center justify-center text-sm font-medium text-lightblue hover:text-blue-400 focus:outline-none focus:ring-2 focus:ring-lightblue"
										>
											View
										</button>
									</div>
								</div>
							),
							{ duration: 10000 }
						)
					}
				}

				ws.onclose = () => {
					// IMPORTANT: Check the flag on the instance that was closed, NOT the ref.
					if (ws.isCleaningUp) {
						console.log(
							"Sidebar: WebSocket closed intentionally on cleanup."
						)
					} else {
						console.log(
							"Sidebar: Notification WebSocket disconnected unexpectedly. Reconnecting..."
						)
						// Clear the ref to allow a new connection to be made.
						wsRef.current = null
						setTimeout(connectWebSocket, 5000) // Attempt to reconnect
					}
				}

				ws.onerror = (error) => {
					console.error(
						"Sidebar: Notification WebSocket error:",
						error
					)
					// The onclose event will fire after an error, triggering the reconnect logic if needed.
					ws.close()
				}
			} catch (error) {
				console.error(
					"Sidebar WS: Failed to initiate connection:",
					error
				)
				setTimeout(connectWebSocket, 5000)
			}
		}

		connectWebSocket()

		// This cleanup function runs when the component unmounts or dependencies change
		return () => {
			if (wsRef.current) {
				console.log(
					"Sidebar: Cleaning up WebSocket connection for effect re-run or unmount."
				)
				wsRef.current.isCleaningUp = true // Mark for intentional close
				wsRef.current.close()
			}
		}
	}, [userDetails?.sub, router]) // Depend only on the stable user ID

	const NavLink = ({ href, icon, label }) => {
		const pathname = usePathname() ?? ""
		const isActive = pathname === href

		return (
			<motion.button
				onClick={() => router.push(href)}
				whileHover={{
					x: 4,
					transition: { duration: 0.15 }
				}}
				whileTap={{ scale: 0.98 }}
				className={cn(
					"flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-[var(--radius-base)] text-sm font-medium transition-all duration-200 group",
					isActive
						? "bg-[var(--color-accent-blue)]/15 text-[var(--color-text-primary)] shadow-sm"
						: "text-[var(--color-text-secondary)] hover:bg-[var(--color-primary-surface-elevated)] hover:text-[var(--color-text-primary)]"
				)}
			>
				<motion.div
					whileHover={{ rotate: isActive ? 0 : -5, scale: 1.1 }}
					transition={{ duration: 0.2 }}
				>
					{icon}
				</motion.div>
				<span className="group-hover:translate-x-0.5 transition-transform duration-150">
					{label}
				</span>
			</motion.button>
		)
	}

	const [isProfileOpen, setProfileOpen] = useState(false)

	return (
		<>
			<motion.div
				initial={{ x: -280 }}
				animate={{ x: isSidebarVisible ? 0 : -281 }}
				transition={{ type: "spring", stiffness: 300, damping: 30 }}
				className="fixed flex flex-col inset-y-0 left-0 z-50 w-[280px] bg-[var(--color-primary-surface)] border-r border-[var(--color-primary-surface-elevated)]"
				onMouseLeave={() =>
					window.innerWidth > 768 && setSidebarVisible(false)
				}
			>
				<div className="flex-1 flex flex-col p-4 overflow-y-auto custom-scrollbar">
					<motion.button
						onClick={() => setSidebarVisible(false)}
						className="absolute top-4 right-4 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] md:hidden p-1 hover:bg-[var(--color-primary-surface-elevated)] rounded-[var(--radius-base)] transition-colors duration-150"
						whileHover={{ scale: 1.1 }}
						whileTap={{ scale: 0.9 }}
					>
						<IconX size={20} />
					</motion.button>

					{/* User Profile Dropdown */}
					<div className="relative mb-6">
						<motion.button
							onClick={() => setProfileOpen(!isProfileOpen)}
							className="flex items-center w-full gap-3 p-3 rounded-[var(--radius-lg)] hover:bg-[var(--color-primary-surface-elevated)] transition-all duration-200 group"
							whileHover={{ scale: 1.02 }}
							whileTap={{ scale: 0.98 }}
						>
							{userDetails?.picture ? (
								<motion.img
									src={userDetails.picture}
									alt="User"
									className="w-9 h-9 rounded-full border-2 border-[var(--color-primary-surface-elevated)]"
									whileHover={{ scale: 1.1 }}
									transition={{ duration: 0.2 }}
								/>
							) : (
								<motion.div
									className="w-9 h-9 rounded-full bg-[var(--color-primary-surface-elevated)] flex items-center justify-center border-2 border-[var(--color-primary-surface-elevated)]"
									whileHover={{ scale: 1.1 }}
									transition={{ duration: 0.2 }}
								>
									<IconUser className="w-5 h-5 text-[var(--color-text-primary)]" />
								</motion.div>
							)}
							<span className="font-semibold text-[var(--color-text-primary)] text-sm flex-1 text-left group-hover:translate-x-0.5 transition-transform duration-150">
								{userDetails?.given_name || "User"}
							</span>
							<motion.div
								animate={{ rotate: isProfileOpen ? 180 : 0 }}
								transition={{ duration: 0.2 }}
							>
								<IconChevronDown className="w-4 h-4 text-[var(--color-text-secondary)] transition-colors duration-150" />
							</motion.div>
						</motion.button>
						<AnimatePresence>
							{isProfileOpen && (
								<motion.div
									initial={{ opacity: 0, y: -10 }}
									animate={{ opacity: 1, y: 0 }}
									exit={{ opacity: 0, y: -10 }}
									className="absolute top-full left-0 right-0 mt-3 bg-[var(--color-primary-surface-elevated)] rounded-[var(--radius-lg)] shadow-xl p-1 z-10"
								>
									<motion.button
										onClick={logout}
										className="flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-[var(--radius-base)] text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-primary-surface)] hover:text-[var(--color-text-primary)]"
									>
										<IconLogout size={16} />
										<span>Logout</span>
									</motion.button>
								</motion.div>
							)}
						</AnimatePresence>
					</div>

					{/* Primary Actions */}
					<div className="flex items-center gap-2 mb-6 px-1">
						<button
							onClick={() => router.push("/tasks?action=add")}
							className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-[var(--radius-base)] bg-[var(--color-accent-red)] text-white text-sm font-semibold hover:bg-red-500 transition-colors"
						>
							<IconPlus size={16} />
							Add task
						</button>
						<button className="p-2.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-primary-surface-elevated)] rounded-[var(--radius-base)] transition-colors">
							<IconSearch size={20} />
						</button>
					</div>

					{/* Main Navigation */}
					<nav className="flex flex-col gap-1 mb-6">
						<NavLink
							href="/home"
							icon={<IconHome size={20} />}
							label="Home"
						/>
						<NavLink
							href="/tasks"
							icon={<IconChecklist size={20} />}
							label="Today"
						/>
						<NavLink
							href="/journal"
							icon={<IconBook size={20} />}
							label="Journal"
						/>
						<NavLink
							href="/notifications"
							icon={<IconBell size={20} />}
							label="Notifications"
						/>
						<NavLink
							href="/settings"
							icon={<IconAdjustments size={20} />}
							label="Settings"
						/>
					</nav>
				</div>
				<div className="p-4 border-t border-[var(--color-primary-surface-elevated)]">
					<div className="flex items-center gap-2">
						<img
							src="/images/half-logo-dark.svg"
							alt="Logo"
							className="w-6 h-6 opacity-70"
						/>
						<span className="text-sm font-medium text-[var(--color-text-tertiary)]">
							Sentient
						</span>
					</div>
				</div>
			</motion.div>
			{/* Desktop hover trigger to show the sidebar */}
			<div
				className="hidden md:block fixed top-0 left-0 h-full w-5 z-40"
				onMouseEnter={() => setSidebarVisible(true)}
			/>
		</>
	)
}

export default Sidebar
