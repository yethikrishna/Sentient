"use client"
import React, { useState, useEffect, useCallback, useRef } from "react"
import { usePathname, useRouter } from "next/navigation"
import { AnimatePresence } from "framer-motion"
import NotificationsOverlay from "@components/NotificationsOverlay"
import { IconMenu2, IconLoader, IconX } from "@tabler/icons-react"
import Sidebar from "@components/Sidebar"
import CommandPalette from "./CommandPallete"
import GlobalSearch from "./GlobalSearch"
import { useGlobalShortcuts } from "@hooks/useGlobalShortcuts"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"

// Helper function to convert VAPID key
function urlBase64ToUint8Array(base64String) {
	const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
	const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
	const rawData = window.atob(base64);
	const outputArray = new Uint8Array(rawData.length);
	for (let i = 0; i < rawData.length; ++i) {
		outputArray[i] = rawData.charCodeAt(i);
	}
	return outputArray;
}
export default function LayoutWrapper({ children }) {
	const [isNotificationsOpen, setNotificationsOpen] = useState(false)
	const [isSearchOpen, setSearchOpen] = useState(false)
	const [isCommandPaletteOpen, setCommandPaletteOpen] = useState(false)
	const [isSidebarCollapsed, setSidebarCollapsed] = useState(true)
	const [isMobileNavOpen, setMobileNavOpen] = useState(false)
	const [unreadCount, setUnreadCount] = useState(0)
	const [userDetails, setUserDetails] = useState(null)
	const wsRef = useRef(null)
	const pathname = usePathname()
	const router = useRouter()

	// State for onboarding check
	const [isLoading, setIsLoading] = useState(true)
	const [isAllowed, setIsAllowed] = useState(false)

	const showNav = !["/", "/onboarding"].includes(pathname)

	useEffect(() => {
		if (!showNav) {
			setIsLoading(false)
			setIsAllowed(true) // Allow rendering for public pages like '/' and '/onboarding'
			return
		}

		const checkStatus = async () => {
			setIsLoading(true)
			try {
				const res = await fetch("/api/user/data")
				if (!res.ok) {
					throw new Error("Session error. Please log in again.")
				}
				const data = await res.json()
				if (data?.data?.onboardingComplete) {
					setIsAllowed(true)
				} else {
					toast.error("Please complete onboarding first.")
					router.push("/onboarding")
					// isAllowed remains false, content won't flash
				}
			} catch (error) {
				toast.error(error.message || "Failed to verify user status.")
				router.push("/") // Redirect to home on error
			} finally {
				setIsLoading(false)
			}
		}

		checkStatus()
	}, [pathname, router, showNav])

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
					if (data.type === "new_notification") {
						setUnreadCount((prev) => prev + 1)
						toast(
							(t) => (
								<div className="flex items-center gap-3">
									<span className="flex-1">
										{data.notification.message}
									</span>
									<button
										onClick={() => {
											handleNotificationsOpen()
											toast.dismiss(t.id)
										}}
										className="py-1 px-3 rounded-md bg-brand-orange text-black text-sm font-semibold"
									>
										View
									</button>
									<button
										onClick={() => toast.dismiss(t.id)}
										className="p-1.5 rounded-full hover:bg-neutral-700"
									>
										<IconX size={16} />
									</button>
								</div>
							),
							{
								duration: 6000
							}
						)
					} else if (data.type === "task_progress_update") {
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

	// PWA Update Handler

	useEffect(() => {
		// This effect runs only on the client side, after the component mounts.
		if (
			"serviceWorker" in navigator &&
			process.env.NODE_ENV !== "development"
		) {
			// The 'load' event ensures that SW registration doesn't delay page rendering.
			window.addEventListener("load", function () {
				navigator.serviceWorker.register("/sw.js").then(
					function (registration) {
						console.log(
							"ServiceWorker registration successful with scope: ",
							registration.scope
						)
					},
					function (err) {
						console.log("ServiceWorker registration failed: ", err)
					}
				)
			})
		}
	}, [])

	// Removed duplicate subscribeToPushNotifications declaration

	// PWA Update Handler
	useEffect(() => {
		if (
			typeof window !== "undefined" &&
			"serviceWorker" in navigator &&
			window.workbox !== undefined
		) {
			const wb = window.workbox

			const promptNewVersionAvailable = (event) => {
				if (!event.wasWaitingBeforeRegister) {
					toast(
						(t) => (
							<div className="flex flex-col items-center gap-2 text-white">
								<span>A new version is available!</span>
								<div className="flex gap-2">
									<button
										className="py-1 px-3 rounded-md bg-green-600 hover:bg-green-500 text-white text-sm font-medium"
										onClick={() => {
											wb.addEventListener(
												"controlling",
												() => {
													window.location.reload()
												}
											)
											wb.messageSkipWaiting()
											toast.dismiss(t.id)
										}}
									>
										Refresh
									</button>
									<button
										className="py-1 px-3 rounded-md bg-neutral-600 hover:bg-neutral-500 text-white text-sm font-medium"
										onClick={() => toast.dismiss(t.id)}
									>
										Dismiss
									</button>
								</div>
							</div>
						),
						{ duration: Infinity }
					)
				}
			}

			wb.addEventListener("waiting", promptNewVersionAvailable)
			return () => {
				wb.removeEventListener("waiting", promptNewVersionAvailable)
			}
		}
	}, [])

	useEffect(() => {
		// This effect runs only on the client side, after the component mounts.
		if (
			"serviceWorker" in navigator &&
			process.env.NODE_ENV === "production"
		) {
			// The 'load' event ensures that SW registration doesn't delay page rendering.
			window.addEventListener("load", function () {
				navigator.serviceWorker.register("/sw.js").then(
					function (registration) {
						console.log(
							"ServiceWorker registration successful with scope: ",
							registration.scope
						)
					},
					function (err) {
						console.log("ServiceWorker registration failed: ", err)
					}
				)
			})
		}
	}, [])

	const subscribeToPushNotifications = useCallback(async () => {
		if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
		if (!process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY) {
			console.warn("VAPID public key not configured. Skipping push subscription.");
			return;
		}
		console.log("VAPID Public Key is configured. Proceeding with push subscription.");

		try {
			const registration = await navigator.serviceWorker.ready;
			console.log("Service Worker is ready:", registration);

			let subscription = await registration.pushManager.getSubscription();
			console.log("Existing subscription:", subscription);

			if (subscription === null) {
				console.log("No existing subscription found. Requesting permission...");
				const permission = await window.Notification.requestPermission();
				console.log("Notification permission status:", permission);

				if (permission !== "granted") return;

				console.log("Permission granted. Subscribing to push manager...");
				subscription = await registration.pushManager.subscribe({
					userVisibleOnly: true,
					applicationServerKey: urlBase64ToUint8Array(process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY),
				});
				console.log("New subscription created:", subscription);

				const response = await fetch("/api/notifications/subscribe", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(subscription),
				});

				if (!response.ok) {
					throw new Error("Failed to send subscription to server.");
				}
				console.log("Subscription successfully sent to server.");
			}
		} catch (error) {
			console.error("Error during push notification subscription:", error);
		}
	}, []);

	useEffect(() => {
		if (showNav && userDetails?.sub) subscribeToPushNotifications()
	}, [showNav, userDetails, subscribeToPushNotifications])

	if (isLoading) {
		return (
			<div className="flex-1 flex h-screen bg-black text-white overflow-hidden justify-center items-center">
				<IconLoader className="w-10 h-10 animate-spin text-brand-orange" />
			</div>
		)
	}

	if (!isAllowed) {
		// This will be shown briefly during the redirect to /onboarding
		return (
			<div className="flex-1 flex h-screen bg-black text-white overflow-hidden justify-center items-center">
				<IconLoader className="w-10 h-10 animate-spin text-brand-orange" />
			</div>
		)
	}
	return (
		<>
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
		</>
	)
}

