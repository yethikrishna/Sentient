// src/client/components/Sidebar.js
"use client"
import { useRouter } from "next/navigation"
import { useEffect, useState, useRef, React } from "react"
import {
	IconChevronRight,
	IconUser,
	IconLogout,
	IconAdjustments,
	IconMessage,
	IconChecklist,
	IconBrain,
	IconNotification,
	IconBell,
	IconX
} from "@tabler/icons-react"
import toast from "react-hot-toast"

const Sidebar = ({ userDetails, setSidebarVisible, isSidebarVisible }) => {
	const router = useRouter()
	const [pricing, setPricing] = useState("free")
	const wsRef = useRef(null)

	const fetchPricingPlan = async () => {
		try {
			const response = await fetch("/api/user/pricing")
			if (!response.ok) throw new Error("Failed to fetch")
			const data = await response.json()
			setPricing(data.pricing || "free")
		} catch (error) {
			toast.error("Error fetching pricing plan.")
		}
	}

	const logout = () => {
		router.push("/api/auth/logout")
	}

	useEffect(() => {
		fetchPricingPlan()

		const connectWebSocket = async () => {
			if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
				return
			}

			try {
				const tokenResponse = await fetch("/api/auth/token")
				if (!tokenResponse.ok) {
					console.error(
						"Sidebar WS: Could not get auth token for WebSocket."
					)
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
									className={`${
										t.visible
											? "animate-enter"
											: "animate-leave"
									} max-w-md w-full bg-neutral-800 shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5 border border-neutral-700`}
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
					console.log(
						"Sidebar: Notification WebSocket disconnected. Will try to reconnect..."
					)
					setTimeout(connectWebSocket, 5000) // Reconnect after 5 seconds
				}

				ws.onerror = (error) => {
					console.error(
						"Sidebar: Notification WebSocket error:",
						error
					)
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

		return () => {
			if (wsRef.current) {
				wsRef.current.close()
			}
		}
	}, [router])

	return (
		<>
			<div
				id="sidebar"
				className={`w-1/5 h-full flex flex-col bg-smokeblack overflow-y-auto transform transition-all duration-300 fixed top-0 left-0 ${isSidebarVisible ? "translate-x-0 opacity-100 z-40 pointer-events-auto" : "-translate-x-full opacity-0 z-0 pointer-events-none"}`}
				onMouseLeave={() => setSidebarVisible(false)}
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
						onClick={() => router.push("/chat")}
						className="cursor-pointer flex items-center gap-3 w-full text-left px-4 py-2 rounded-lg text-white hover:text-lightblue hover:bg-neutral-800 mt-1"
					>
						<IconMessage className="w-5 h-5" />
						<span className="text-base text-white">Chat</span>
					</button>

					<button
						onClick={() => router.push("/tasks")}
						className="cursor-pointer flex items-center gap-3 w-full text-left px-4 py-2 rounded-lg text-white hover:text-lightblue hover:bg-neutral-800 mt-1"
					>
						<IconChecklist className="w-5 h-5" />
						<span className="text-base text-white">Tasks</span>
					</button>
					<button
						onClick={() => router.push("/memory")}
						className="cursor-pointer flex items-center gap-3 w-full text-left px-4 py-2 rounded-lg text-white hover:text-lightblue hover:bg-neutral-800 mt-1"
					>
						<IconBrain className="w-5 h-5" />
						<span className="text-base text-white">Memories</span>
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
					<div className="mt-auto mb-6 mx-2">
						<div className="bg-gradient-to-br from-darkblue to-lightblue rounded-xl p-4 relative overflow-hidden">
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
			<div
				className="fixed top-0 left-0 bg-transparent w-[5%] h-full z-30 flex items-center justify-start"
				onMouseEnter={() => setSidebarVisible(true)}
			>
				<div className="ml-3">
					<IconChevronRight className="text-white w-6 h-6 animate-pulse font-bold" />
				</div>
			</div>
		</>
	)
}

export default Sidebar
