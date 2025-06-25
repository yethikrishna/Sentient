"use client"
import { useRouter } from "next/navigation"
import { useEffect, useState, useRef, useCallback } from "react"
import {
	IconChevronLeft,
	IconUser,
	IconLogout,
	IconAdjustments,
	IconMessage,
	IconChecklist,
	IconNotification,
	IconBell,
	IconBook,
	IconHome
} from "@tabler/icons-react"
import toast from "react-hot-toast"

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
		router.push("/api/auth/logout")
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

	return (
		<>
			<div
				className={`fixed flex flex-col justify-between inset-y-0 left-0 z-40 w-80 md:w-96 bg-smokeblack transform transition-transform duration-300 ease-in-out ${
					isSidebarVisible ? "translate-x-0" : "-translate-x-full"
				}`}
			>
				<div className="flex items-center px-6 py-6">
					<div className="flex items-center justify-center rounded-xl w-12 h-12">
						<img
							src="/images/half-logo-dark.svg"
							alt="Logo"
							className="w-8 h-8"
						/>
					</div>
					<span className="text-2xl text-white font-extralight ml-3">
						Sentient
					</span>
				</div>
				<div className="flex flex-col px-4 pt-4 pb-8 flex-grow">
					<button
						onClick={() => setSidebarVisible(false)}
						className="absolute top-4 right-4 text-gray-400 hover:text-white"
					>
						<IconChevronLeft />
					</button>
					<button
						onClick={() => router.push("/home")}
						className="cursor-pointer flex items-center gap-3 w-full text-left px-4 py-2 rounded-lg text-white hover:text-lightblue hover:bg-neutral-800 mt-1"
					>
						<IconHome className="w-5 h-5" />
						<span className="text-base text-white">Home</span>
					</button>
					<button // New Journal link
						onClick={() => router.push("/journal")}
						className="cursor-pointer flex items-center gap-3 w-full text-left px-4 py-2 rounded-lg text-white hover:text-lightblue hover:bg-neutral-800 mt-1"
					>
						<IconBook className="w-5 h-5" />
						<span className="text-base text-white">Journal</span>
					</button>

					<button
						onClick={() => router.push("/tasks")}
						className="cursor-pointer flex items-center gap-3 w-full text-left px-4 py-2 rounded-lg text-white hover:text-lightblue hover:bg-neutral-800 mt-1"
					>
						<IconChecklist className="w-5 h-5" />
						<span className="text-base text-white">Tasks</span>
					</button>
					<button
						onClick={() => router.push("/settings")}
						className="cursor-pointer flex items-center gap-3 w-full text-left px-4 py-2 rounded-lg text-white hover:text-lightblue hover:bg-neutral-800 mt-1"
					>
						<IconAdjustments className="w-5 h-5" />
						<span className="text-base text-white">Settings</span>
					</button>
					<button
						onClick={() => router.push("/notifications")}
						className="cursor-pointer flex items-center gap-3 w-full text-left px-4 py-2 rounded-lg text-white hover:text-lightblue hover:bg-neutral-800 mt-1"
					>
						<IconNotification className="w-5 h-5" />
						<span className="text-base text-white">
							Notifications
						</span>
					</button>

					{/* Chat history removed */}

					<div className="mt-auto mb-6 mx-2 pt-6">
						<div className="bg-gradient-to-br from-darkblue to-lightblue rounded-xl p-4 relative overflow-hidden mt-4">
							<div className="absolute top-0 right-0 w-24 h-24 rounded-full bg-white opacity-10 -mr-8 -mt-8"></div>
							<div className="flex items-center mb-2">
								<div className="bg-white bg-opacity-20 p-1 rounded-lg">
									<img
										src="/images/half-logo-dark.svg"
										alt="Logo"
										className="w-6 h-6"
									/>
								</div>
								<span className="text-xl font-bold text-white ml-2">
									Pro Plan
								</span>
							</div>
							<p className="text-white text-sm mb-4">
								Unlimited access to all features!
							</p>
							<div className="flex items-center justify-between">
								<span className="text-white font-bold">
									$3 / mo
								</span>
								<button
									onClick={() => router.push("/settings")}
									className="bg-white text-black font-medium py-1 px-4 rounded-full"
								>
									Get
								</button>
							</div>
						</div>
					</div>
					<button
						onClick={logout}
						className="flex items-center justify-between px-6 py-2 text-[#9ca3af] hover:text-white"
					>
						<span className="text-base">Log out</span>
						<IconLogout className="w-5 h-5" />
					</button>
				</div>
				<div className="px-6 py-3 mt-auto border-t border-[#373a43]">
					<div className="flex items-center space-x-3">
						{userDetails?.picture ? (
							<img
								src={userDetails.picture}
								alt="User"
								className="w-10 h-10 rounded-full"
							/>
						) : (
							<div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
								<IconUser className="w-6 h-6 text-white" />
							</div>
						)}
						<div>
							<p className="text-white font-semibold">
								{userDetails?.given_name || "User"}
							</p>
							<p className="text-sm text-gray-400">
								{pricing.charAt(0).toUpperCase() +
									pricing.slice(1)}{" "}
								Plan
							</p>
						</div>
					</div>
				</div>
			</div>
			{/* Desktop hover trigger to show the sidebar */}
			<div
				className="hidden md:block fixed top-0 left-0 h-full w-8 z-30"
				onMouseEnter={() => setSidebarVisible(true)}
			/>
		</>
	)
}

export default Sidebar
