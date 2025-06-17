"use client"
import React, { useState, useEffect, useRef, useCallback, use } from "react"
import { useRouter } from "next/navigation"
import ChatBubble from "@components/ChatBubble"
import ToolResultBubble from "@components/ToolResultBubble"
import Sidebar from "@components/Sidebar"
import {
	IconSend,
	IconLoader,
	IconMail,
	IconBrandGoogleDrive,
	IconBrandSlack,
	IconBrandNotion,
	IconNews,
	IconCloud,
	IconWorldSearch,
	IconCalendarEvent,
	IconPlayerStopFilled,
	IconPhone,
	IconPhoneOff,
	IconMicrophone,
	IconFileText,
	IconPresentation,
	IconTable,
	IconMessageOff,
	IconMap,
	IconShoppingCart
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import GmailSearchResults from "@components/agents/GmailSearchResults"
import BackgroundCircleProvider from "@components/voice-visualization/background-circle-provider"
import { cn } from "@utils/cn"

const integrationIcons = {
	gmail: IconMail,
	gcalendar: IconCalendarEvent,
	gdrive: IconBrandGoogleDrive,
	gdocs: IconFileText,
	gslides: IconPresentation,
	gsheets: IconTable,
	slack: IconBrandSlack,
	notion: IconBrandNotion
}

const Chat = ({ params }) => {
	const router = useRouter()
	// The chatId is the first element of the catch-all route segment
	const chatIdFromParams = use(params)

	// --- State Variables ---
	const [messages, setMessages] = useState([])
	const [input, setInput] = useState("")
	const [userDetails, setUserDetails] = useState(null)
	const [thinking, setThinking] = useState(false)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [currentChatId, setCurrentChatId] = useState(chatIdFromParams)
	const [isNewChat, setIsNewChat] = useState(!chatIdFromParams)
	const [isLoading, setIsLoading] = useState(!!chatIdFromParams) // Only load if it's an existing chat
	const [isVoiceMode, setIsVoiceMode] = useState(false)

	const [connectionStatus, setConnectionStatus] = useState("disconnected")
	const [audioInputDevices, setAudioInputDevices] = useState([])
	const [selectedAudioInputDevice, setSelectedAudioInputDevice] = useState("")
	const [connectedIntegrations, setConnectedIntegrations] = useState([])
	const [voiceStatusText, setVoiceStatusText] = useState("Click to Start")
	const [isInternetEnabled, setInternetEnabled] = useState(false)
	const [isWeatherEnabled, setWeatherEnabled] = useState(false)
	const [isNewsEnabled, setNewsEnabled] = useState(false)
	const [isMapsEnabled, setMapsEnabled] = useState(false)
	const [isShoppingEnabled, setShoppingEnabled] = useState(false)

	// --- Refs ---
	const textareaRef = useRef(null)
	const chatEndRef = useRef(null)
	const backgroundCircleProviderRef = useRef(null)
	const ringtoneAudioRef = useRef(null)
	const connectedAudioRef = useRef(null)
	const remoteAudioRef = useRef(null) // To play the AI's voice
	const abortControllerRef = useRef(null)

	// --- Handlers ---
	const handleInputChange = (e) => {
		const value = e.target.value
		setInput(value)
		if (textareaRef.current) {
			textareaRef.current.style.height = "auto"
			textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
		}
	}

	const handleStatusChange = useCallback((status) => {
		setConnectionStatus(status)
		if (status !== "connecting" && ringtoneAudioRef.current) {
			ringtoneAudioRef.current.pause()
			ringtoneAudioRef.current.currentTime = 0
		}
		if (status === "connected" && connectedAudioRef.current) {
			connectedAudioRef.current.volume = 0.4
			connectedAudioRef.current
				.play()
				.catch((e) => console.error("Error playing sound:", e))
			setVoiceStatusText("Listening...")
		} else if (status === "disconnected") {
			setVoiceStatusText("Click to Start")
		} else if (status === "connecting") {
			setVoiceStatusText("Connecting...")
		}
	}, [])

	const handleVoiceEvent = useCallback((event) => {
		if (event.type === "chat_created" && event.chatId) {
			window.history.replaceState(null, "", `/chat/${event.chatId}`)
			setCurrentChatId(event.chatId)
			setIsNewChat(false)
		} else if (event.type === "stt_result" && event.text) {
			setMessages((prev) => [
				...prev,
				{
					id: `user_${Date.now()}`,
					message: event.text,
					isUser: true,
					type: "text"
				}
			])
		} else if (event.type === "llm_result" && event.text) {
			setMessages((prev) => [
				...prev,
				{
					id: event.messageId || `asst_${Date.now()}`,
					message: event.text,
					isUser: false,
					type: "text"
				}
			])
		} else if (event.type === "status") {
			if (event.message === "thinking") setVoiceStatusText("Thinking...")
			else if (event.message === "speaking")
				setVoiceStatusText("Speaking...")
			else if (event.message === "listening")
				setVoiceStatusText("Listening...")
		} else if (event.type === "error") {
			toast.error(`Voice Error: ${event.message}`)
			setVoiceStatusText("Error. Click to retry.")
		}
	}, [])

	// This new handler will be passed to the WebRTC client to attach the remote audio stream
	const handleRemoteAudioStream = useCallback((stream) => {
		if (remoteAudioRef.current) {
			console.log("Attaching remote audio stream to audio element.")
			remoteAudioRef.current.srcObject = stream
			remoteAudioRef.current
				.play()
				.catch((e) => console.error("Error playing remote audio:", e))
		}
	}, [])

	const handleStartVoice = async () => {
		if (
			connectionStatus !== "disconnected" ||
			!backgroundCircleProviderRef.current
		)
			return
		setConnectionStatus("connecting")
		try {
			const tokenResponse = await fetch("/api/auth/token")
			if (!tokenResponse.ok) throw new Error("Could not get auth token.")
			const { accessToken } = await tokenResponse.json()
			if (ringtoneAudioRef.current) {
				ringtoneAudioRef.current.volume = 0.3
				ringtoneAudioRef.current.loop = true // Keep ringing
				ringtoneAudioRef.current
					.play()
					.catch((e) => console.error("Error playing ringtone:", e))
			}
			await backgroundCircleProviderRef.current?.connect(
				selectedAudioInputDevice,
				accessToken,
				currentChatId
			)
		} catch (error) {
			console.error("Error during voice connection process:", error)
			toast.error(
				`Connection failed: ${error.message || "Please check console for details."}`
			)
			handleStatusChange("disconnected")
		}
	}

	const handleStopVoice = () => {
		if (
			connectionStatus === "disconnected" ||
			!backgroundCircleProviderRef.current
		)
			return
		backgroundCircleProviderRef.current?.disconnect()
	}

	const toggleVoiceMode = () => {
		if (isVoiceMode) {
			handleStopVoice()
		}
		setIsVoiceMode(!isVoiceMode)
	}

	const fetchChatHistory = useCallback(async () => {
		if (!currentChatId) {
			setIsLoading(false)
			return
		}
		setIsLoading(true)
		try {
			const response = await fetch("/api/chat/history", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ chatId: currentChatId })
			})
			if (response.ok) {
				const data = await response.json()
				setMessages(data.messages || [])
			} else {
				toast.error("Error fetching chat history.")
				setMessages([])
			}
		} catch (error) {
			toast.error("Error fetching chat history.")
		} finally {
			setIsLoading(false)
		}
	}, [currentChatId])

	const fetchUserDetails = async () => {
		try {
			const response = await fetch("/api/user/profile") // Corrected endpoint
			if (!response.ok) {
				throw new Error("Failed to fetch user details")
			}
			const data = await response.json()
			setUserDetails(data)
		} catch (error) {
			console.error("Error fetching user details:", error)
			toast.error("Error fetching user details.")
		}
	}

	const fetchConnectedIntegrations = async () => {
		try {
			const response = await fetch("/api/integrations/connected")
			if (response.ok) {
				const data = await response.json()
				const connected = (data.integrations || []) // Corrected data access
					.filter(
						(i) =>
							i.connected &&
							(i.auth_type === "oauth" ||
								i.auth_type === "manual")
					)
					.map((i) => ({ ...i, icon: integrationIcons[i.name] }))
				setConnectedIntegrations(connected)
			}
		} catch (error) {
			console.error("Failed to fetch connected integrations", error)
		}
	}

	const sendMessage = async () => {
		if (input.trim() === "") return
		const newUserMessage = {
			message: input,
			isUser: true,
			id: Date.now(),
			type: "text"
		}
		setMessages((prev) => [...prev, newUserMessage])
		const currentInput = input
		setInput("")
		if (textareaRef.current) textareaRef.current.style.height = "auto"
		setThinking(true)
		abortControllerRef.current = new AbortController()
		try {
			const response = await fetch("/api/chat/message", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					input: currentInput,
					chatId: currentChatId,
					enable_internet: isInternetEnabled,
					enable_weather: isWeatherEnabled,
					enable_news: isNewsEnabled,
					enable_maps: isMapsEnabled,
					enable_shopping: isShoppingEnabled
				}),
				signal: abortControllerRef.current.signal
			})
			if (!response.ok || !response.body) {
				const errorData = await response
					.json()
					.catch(() => ({ message: "An unknown error occurred" }))
				throw new Error(
					errorData.message || "Failed to get streaming response"
				)
			}
			const reader = response.body.getReader()
			const decoder = new TextDecoder()
			let assistantMessageId = null
			let buffer = ""
			while (true) {
				const { value, done } = await reader.read()
				if (done) break
				buffer += decoder.decode(value, { stream: true })
				let newlineIndex
				while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
					const line = buffer.slice(0, newlineIndex)
					buffer = buffer.slice(newlineIndex + 1)
					if (line.trim() === "") continue
					try {
						const parsed = JSON.parse(line)
						if (parsed.type === "error") {
							toast.error(`An error occurred: ${parsed.message}`)
							continue
						}
						// New event to handle chat creation
						if (parsed.type === "chat_created") {
							window.history.replaceState(
								null,
								"",
								`/chat/${parsed.chatId}`
							)
							setCurrentChatId(parsed.chatId)
							setIsNewChat(false)
							// Optional: Add to sidebar chat list dynamically
						} else if (
							parsed.type === "agent_step" ||
							parsed.type === "gmail_search"
						) {
							setMessages((prev) => [
								...prev,
								{ ...parsed, isUser: false }
							])
						} else if (parsed.type === "assistantStream") {
							const token = parsed.token || parsed.message || ""
							assistantMessageId = parsed.messageId
							setMessages((prev) => {
								const existingMsgIndex = prev.findIndex(
									(msg) => msg.id === assistantMessageId
								)
								if (existingMsgIndex !== -1) {
									return prev.map((msg, index) =>
										index === existingMsgIndex
											? {
													...msg,
													message: msg.message + token
												}
											: msg
									)
								} else {
									return [
										...prev,
										{
											id: assistantMessageId,
											message: token,
											isUser: false,
											type: "text",
											memoryUsed: parsed.memoryUsed,
											agentsUsed: parsed.agentsUsed,
											internetUsed: parsed.internetUsed
										}
									]
								}
							})
						}
					} catch (e) {
						console.error(
							"Error parsing stream data:",
							e,
							"Line:",
							line
						)
					}
				}
			}
		} catch (error) {
			if (error.name !== "AbortError")
				toast.error(`Error: ${error.message}`)
		} finally {
			setThinking(false)
		}
	}

	const handleStopStreaming = () => {
		if (abortControllerRef.current) {
			abortControllerRef.current.abort()
			setMessages((prev) => {
				const lastMessage = prev[prev.length - 1]
				if (lastMessage && !lastMessage.isUser) {
					lastMessage.message += "\n\n[STREAM STOPPED BY USER]"
				}
				return [...prev]
			})
		}
	}

	// Effect for one-time setup and teardown
	useEffect(() => {
		fetchUserDetails()
		fetchConnectedIntegrations()
		const getDevices = async () => {
			try {
				if (
					!navigator.mediaDevices ||
					!navigator.mediaDevices.enumerateDevices
				)
					return
				// Request microphone permission
				await navigator.mediaDevices.getUserMedia({
					audio: true,
					video: false
				})
				const devices = await navigator.mediaDevices.enumerateDevices()
				const audioInputDevices = devices.filter(
					(d) => d.kind === "audioinput"
				)
				if (audioInputDevices.length > 0) {
					setAudioInputDevices(
						audioInputDevices.map((d, i) => ({
							deviceId: d.deviceId,
							label: d.label || `Microphone ${i + 1}`
						}))
					)
					if (!selectedAudioInputDevice)
						setSelectedAudioInputDevice(
							audioInputDevices[0].deviceId
						)
				}
			} catch (error) {
				toast.error(
					"Could not get microphone list. Please grant permission."
				)
			}
		}
		getDevices()

		return () => {
			if (abortControllerRef.current) abortControllerRef.current.abort()
			if (
				backgroundCircleProviderRef.current &&
				connectionStatus !== "disconnected"
			) {
				backgroundCircleProviderRef.current.disconnect()
			}
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [])

	// Effect to fetch history when chat ID changes
	useEffect(() => {
		if (currentChatId) {
			setIsNewChat(false)
			fetchChatHistory()
		} else {
			// This is a new chat
			setIsNewChat(true)
			setMessages([])
			setIsLoading(false)
		}
	}, [currentChatId, fetchChatHistory])

	// Effect to scroll to the bottom of the chat
	useEffect(() => {
		if (chatEndRef.current)
			chatEndRef.current.scrollIntoView({ behavior: "smooth" })
	}, [messages])

	return (
		<div className="h-screen bg-matteblack relative overflow-hidden dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>

			<div className="absolute inset-0 flex flex-col justify-center items-center h-full w-full bg-matteblack z-10 pt-4 pb-4">
				<div className="w-full h-full flex flex-col items-center justify-center p-5 text-white">
					{isLoading ? (
						<div className="flex justify-center items-center h-full w-full">
							<IconLoader className="w-10 h-10 text-white animate-spin" />
						</div>
					) : (
						<div
							className={cn(
								"w-full h-full flex flex-col",
								isNewChat || isVoiceMode
									? "items-center justify-center"
									: "max-w-4xl"
							)}
						>
							{isVoiceMode ? (
								<div className="relative flex h-full w-full flex-col items-center justify-center">
									<BackgroundCircleProvider
										ref={backgroundCircleProviderRef}
										onStatusChange={handleStatusChange}
										onEvent={handleVoiceEvent}
										connectionStatusProp={connectionStatus}
										onAudioStream={handleRemoteAudioStream}
									/>
									<div className="absolute inset-0 z-20 flex flex-col items-center justify-center pointer-events-none">
										<div className="pointer-events-auto flex flex-col items-center gap-4">
											{connectionStatus ===
											"disconnected" ? (
												<button
													onClick={handleStartVoice}
													className="flex h-32 w-32 items-center justify-center rounded-full bg-green-600 text-white shadow-lg transition-colors duration-200 hover:bg-green-500"
													title="Start Call"
												>
													<IconPhone size={48} />
												</button>
											) : connectionStatus ===
											  "connecting" ? (
												<div className="flex h-32 w-32 items-center justify-center rounded-full bg-yellow-600 text-white shadow-lg">
													<IconLoader
														size={48}
														className="animate-spin"
													/>
												</div>
											) : (
												<button
													onClick={handleStopVoice}
													className="flex h-32 w-32 items-center justify-center rounded-full bg-red-600 text-white shadow-lg transition-colors duration-200 hover:bg-red-500"
													title="Hang Up"
												>
													<IconPhoneOff size={48} />
												</button>
											)}
											<p className="mt-4 text-center text-lg font-medium text-gray-300">
												{voiceStatusText}
											</p>
										</div>
									</div>
									<div className="absolute bottom-[25%] max-w-2xl text-center">
										{messages
											.filter((m) => !m.isUser)
											.slice(-1)
											.map((msg) => (
												<p
													key={msg.id}
													className="text-gray-400"
												>
													{msg.message}
												</p>
											))}
										{messages
											.filter((m) => m.isUser)
											.slice(-1)
											.map((msg) => (
												<p
													key={msg.id}
													className="text-2xl font-semibold text-white"
												>
													{msg.message}
												</p>
											))}
									</div>
								</div>
							) : (
								<>
									<div className="grow overflow-y-auto p-4 rounded-xl no-scrollbar mb-4 flex flex-col gap-4 w-full">
										{messages.length === 0 && !thinking ? (
											<div
												className={cn(
													"font-Poppins flex flex-col justify-center items-center text-gray-400",
													isNewChat
														? "h-full"
														: "h-auto py-10"
												)}
											>
												<p className="text-3xl text-white mb-4">
													{isNewChat
														? "Ask me anything."
														: "Send a message to start"}
												</p>
											</div>
										) : (
											messages.map((msg) => (
												<div
													key={msg.id}
													className={`flex ${msg.isUser ? "justify-end" : "justify-start"} w-full`}
												>
													{msg.type ===
													"agent_step" ? (
														<ToolResultBubble
															task={msg.task}
															result={msg.message}
															memoryUsed={
																msg.memoryUsed
															}
															agentsUsed={
																msg.agentsUsed
															}
															internetUsed={
																msg.internetUsed
															}
														/>
													) : msg.type ===
													  "gmail_search" ? (
														<GmailSearchResults
															emails={
																msg.message
																	.email_data
															}
															gmailSearchUrl={
																msg.message
																	.gmail_search_url
															}
														/>
													) : (
														<ChatBubble
															message={
																msg.message
															}
															isUser={msg.isUser}
															memoryUsed={
																msg.memoryUsed
															}
															agentsUsed={
																msg.agentsUsed
															}
															internetUsed={
																msg.internetUsed
															}
														/>
													)}
												</div>
											))
										)}
										{thinking && (
											<div className="flex justify-start w-full mt-2">
												<div className="flex items-center gap-2 p-3 bg-gray-700 rounded-lg">
													<div className="bg-gray-400 rounded-full h-2 w-2 animate-pulse delay-75"></div>
													<div className="bg-gray-400 rounded-full h-2 w-2 animate-pulse delay-150"></div>
													<div className="bg-gray-400 rounded-full h-2 w-2 animate-pulse delay-300"></div>
												</div>
											</div>
										)}
										<div ref={chatEndRef} />
									</div>

									<div
										className={cn(
											"w-full px-4",
											isNewChat ? "max-w-4xl" : ""
										)}
									>
										{/* Tool Toggles & Info */}
										<div className="flex flex-col items-center">
											<div className="flex items-center flex-wrap justify-center gap-4 mb-3 text-xs text-gray-400">
												<label
													htmlFor="internet-toggle"
													className="flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors"
												>
													<IconWorldSearch
														size={16}
														className={
															isInternetEnabled
																? "text-lightblue"
																: ""
														}
													/>
													<span>Internet</span>
													<Switch
														checked={
															isInternetEnabled
														}
														onCheckedChange={
															setInternetEnabled
														}
													/>
												</label>
												<label
													htmlFor="weather-toggle"
													className="flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors"
												>
													<IconCloud
														size={16}
														className={
															isWeatherEnabled
																? "text-lightblue"
																: ""
														}
													/>
													<span>Weather</span>
													<Switch
														checked={
															isWeatherEnabled
														}
														onCheckedChange={
															setWeatherEnabled
														}
													/>
												</label>
												<label
													htmlFor="news-toggle"
													className="flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors"
												>
													<IconNews
														size={16}
														className={
															isNewsEnabled
																? "text-lightblue"
																: ""
														}
													/>
													<span>News</span>
													<Switch
														checked={isNewsEnabled}
														onCheckedChange={
															setNewsEnabled
														}
													/>
												</label>
												<label
													htmlFor="maps-toggle"
													className="flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors"
												>
													<IconMap
														size={16}
														className={
															isMapsEnabled
																? "text-lightblue"
																: ""
														}
													/>
													<span>Maps</span>
													<Switch
														checked={isMapsEnabled}
														onCheckedChange={
															setMapsEnabled
														}
													/>
												</label>
												<label
													htmlFor="shopping-toggle"
													className="flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors"
												>
													<IconShoppingCart
														size={16}
														className={
															isShoppingEnabled
																? "text-lightblue"
																: ""
														}
													/>
													<span>Shopping</span>
													<Switch
														checked={
															isShoppingEnabled
														}
														onCheckedChange={
															setShoppingEnabled
														}
													/>
												</label>
											</div>
											{connectedIntegrations.length >
												0 && (
												<div className="flex items-center gap-2 mb-2 text-xs text-gray-500">
													<span>
														Tools connected:
													</span>
													<div className="flex items-center gap-1.5">
														{connectedIntegrations.map(
															(integ) => {
																const Icon =
																	integ.icon
																return (
																	Icon && (
																		<Icon
																			key={
																				integ.name
																			}
																			size={
																				16
																			}
																			title={
																				integ.display_name
																			}
																		/>
																	)
																)
															}
														)}
													</div>
												</div>
											)}
										</div>
										<div className="relative w-full flex flex-row gap-4 items-end px-4 py-2 bg-matteblack border-[1px] border-gray-600 rounded-lg z-10">
											<textarea
												ref={textareaRef}
												value={input}
												onChange={handleInputChange}
												onKeyDown={(e) => {
													if (
														e.key === "Enter" &&
														!e.shiftKey
													) {
														e.preventDefault()
														sendMessage()
													}
												}}
												className="flex-grow p-2 pr-28 rounded-lg bg-transparent text-base text-white focus:outline-none resize-none no-scrollbar overflow-y-auto"
												placeholder="Type your message..."
												style={{
													maxHeight: "150px",
													minHeight: "24px"
												}}
												rows={1}
											/>
											<div className="absolute right-4 bottom-3 flex flex-row items-center gap-2">
												{thinking ? (
													<button
														onClick={
															handleStopStreaming
														}
														className="p-2 hover-button scale-100 hover:scale-110 cursor-pointer rounded-full text-white bg-red-600 hover:bg-red-500"
														title="Stop Generation"
													>
														<IconPlayerStopFilled className="w-4 h-4 text-white" />
													</button>
												) : (
													<button
														onClick={sendMessage}
														disabled={
															input.trim() === ""
														}
														className="p-2 hover-button scale-100 hover:scale-110 cursor-pointer rounded-full text-white disabled:opacity-50 disabled:cursor-not-allowed"
														title="Send Message"
													>
														<IconSend className="w-4 h-4 text-white" />
													</button>
												)}
												<button
													onClick={toggleVoiceMode}
													className="p-2 hover-button scale-100 hover:scale-110 cursor-pointer rounded-full text-white"
													title="Switch to Voice Mode"
												>
													<IconMicrophone className="w-4 h-4 text-white" />
												</button>
											</div>
										</div>
									</div>
								</>
							)}
						</div>
					)}
				</div>
			</div>
			{!isLoading && !isNewChat && (
				<div className="absolute bottom-6 right-6 z-30 flex items-center gap-2">
					<button
						onClick={toggleVoiceMode}
						className="p-2.5 rounded-full bg-neutral-700/80 backdrop-blur-sm hover:bg-lightblue text-white shadow-lg"
						title={
							isVoiceMode
								? "Switch to Text Mode"
								: "Switch to Voice Mode"
						}
					>
						{isVoiceMode ? (
							<IconMessageOff size={18} />
						) : (
							<IconMicrophone size={18} />
						)}
					</button>
					{isVoiceMode && (
						<select
							value={selectedAudioInputDevice}
							onChange={(e) =>
								setSelectedAudioInputDevice(e.target.value)
							}
							className="bg-neutral-700/80 backdrop-blur-sm border border-neutral-600 text-white text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-lightblue appearance-none max-w-[200px] truncate shadow-lg"
							title="Select Microphone"
							disabled={connectionStatus !== "disconnected"}
						>
							{audioInputDevices.length === 0 ? (
								<option value="">No mics found</option>
							) : (
								audioInputDevices.map((device) => (
									<option
										key={device.deviceId}
										value={device.deviceId}
									>
										{device.label}
									</option>
								))
							)}
						</select>
					)}
				</div>
			)}
			<audio
				ref={ringtoneAudioRef}
				src="/audio/ringing.mp3"
				preload="auto"
				loop
			></audio>
			<audio
				ref={connectedAudioRef}
				src="/audio/connected.mp3"
				preload="auto"
			></audio>
			{/* This audio element will play the remote stream from the server (the AI's voice) */}
			<audio ref={remoteAudioRef} autoPlay></audio>
		</div>
	)
}

const Switch = ({ checked, onCheckedChange }) => (
	<button
		type="button"
		role="switch"
		aria-checked={checked}
		onClick={() => onCheckedChange(!checked)}
		className={cn(
			"relative inline-flex h-[18px] w-[34px] flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-lightblue focus:ring-offset-2 focus:ring-offset-matteblack",
			checked ? "bg-lightblue" : "bg-neutral-600"
		)}
	>
		<span
			aria-hidden="true"
			className={cn(
				"pointer-events-none inline-block h-[14px] w-[14px] transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
				checked ? "translate-x-[16px]" : "translate-x-0"
			)}
		/>
	</button>
)

export default Chat
