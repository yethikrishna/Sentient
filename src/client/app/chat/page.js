// src/client/app/chat/page.js
"use client"
import React, { useState, useEffect, useRef, useCallback } from "react"
import ChatBubble from "@components/ChatBubble"
import ToolResultBubble from "@components/ToolResultBubble"
import Sidebar from "@components/Sidebar"
import TopControlBar from "@components/TopControlBar"
import {
	IconSend,
	IconRefresh,
	IconLoader,
	IconPhone,
	IconPhoneOff
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import BackgroundCircleProvider from "@components/voice-visualization/background-circle-provider"

const Chat = () => {
	// --- State Variables ---
	const [messages, setMessages] = useState([])
	const [input, setInput] = useState("")
	const [userDetails, setUserDetails] = useState(null)
	const [thinking, setThinking] = useState(false)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [chatMode, setChatMode] = useState("text")
	const [isLoading, setIsLoading] = useState(() => chatMode === "text")
	const [connectionStatus, setConnectionStatus] = useState("disconnected")
	const [audioInputDevices, setAudioInputDevices] = useState([])
	const [selectedAudioInputDevice, setSelectedAudioInputDevice] = useState("")

	// --- Refs ---
	const textareaRef = useRef(null)
	const chatEndRef = useRef(null)
	const backgroundCircleProviderRef = useRef(null)
	const ringtoneAudioRef = useRef(null)
	const connectedAudioRef = useRef(null)
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

	const handleToggleMode = (targetMode) => {
		if (targetMode === chatMode) return
		setChatMode(targetMode)
		if (targetMode === "text" && connectionStatus !== "disconnected") {
			handleStopVoice()
		}
	}

	// --- Connection Status and Timer Handling ---
	const handleStatusChange = useCallback((status) => {
		console.log("Connection status changed:", status)
		setConnectionStatus(status)

		if (status !== "connecting" && ringtoneAudioRef.current) {
			ringtoneAudioRef.current.pause()
			ringtoneAudioRef.current.currentTime = 0
		}

		if (status === "connected") {
			if (connectedAudioRef.current) {
				connectedAudioRef.current.volume = 0.4
				connectedAudioRef.current
					.play()
					.catch((e) =>
						console.error("Error playing connected sound:", e)
					)
			}
		}
	}, [])

	// --- Voice Control Handlers ---
	const handleStartVoice = async () => {
		if (
			connectionStatus !== "disconnected" ||
			!backgroundCircleProviderRef.current
		)
			return
		console.log("ChatPage: handleStartVoice called")
		setConnectionStatus("connecting")
		if (ringtoneAudioRef.current) {
			ringtoneAudioRef.current.volume = 0.3
			ringtoneAudioRef.current.loop = true
			ringtoneAudioRef.current
				.play()
				.catch((e) => console.error("Error playing ringtone:", e))
		}
		try {
			await backgroundCircleProviderRef.current?.connect()
		} catch (error) {
			console.error("ChatPage: Error starting voice connection:", error)
			toast.error(
				`Failed to connect: ${error.message || "Unknown error"}`
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
		console.log("ChatPage: handleStopVoice called")
		backgroundCircleProviderRef.current?.disconnect()
	}

	const handleDeviceChange = (event) => {
		const deviceId = event.target.value
		console.log("ChatPage: Selected audio input device changed:", deviceId)
		setSelectedAudioInputDevice(deviceId)
		toast.success(
			"Microphone selection changed. Please restart the call to use the new device.",
			{ duration: 4000 }
		)
	}

	// --- Data Fetching and API Calls ---
	const fetchChatHistory = async () => {
		try {
			const response = await fetch("/api/chat/history")
			if (response.ok) {
				const data = await response.json()
				console.log(
					"fetchChatHistory: Received history",
					data.messages?.length
				)
				setMessages(data.messages || [])
			} else {
				const errorData = await response.json()
				console.error(
					"fetchChatHistory: Error from API:",
					errorData.message
				)
				toast.error(`Error fetching chat history: ${errorData.message}`)
				setMessages([])
			}
		} catch (error) {
			console.error("fetchChatHistory: Exception caught:", error)
			toast.error("Error fetching chat history.")
			setMessages([])
		} finally {
			console.log(
				"fetchChatHistory: Setting isLoading to false in finally block."
			)
			setIsLoading(false)
		}
	}

	const fetchUserDetails = async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) {
				throw new Error("Failed to fetch user details")
			}
			const data = await response.json()
			setUserDetails(data)
		} catch (error) {
			toast.error("Error fetching user details.")
		}
	}

	const sendMessage = async () => {
		if (input.trim() === "" || chatMode !== "text") return

		const newUserMessage = {
			message: input,
			isUser: true,
			id: Date.now(),
			type: "text"
		}
		setMessages((prev) => [...prev, newUserMessage])
		const currentInput = input
		setInput("")
		if (textareaRef.current) {
			textareaRef.current.style.height = "auto"
		}
		setThinking(true)

		abortControllerRef.current = new AbortController()

		try {
			const response = await fetch("/api/chat/message", {
				method: "POST",
				headers: {
					"Content-Type": "application/json"
				},
				body: JSON.stringify({ input: currentInput }),
				signal: abortControllerRef.current.signal
			})

			if (!response.ok || !response.body) {
				const errorData = await response.json()
				throw new Error(
					errorData.message || "Failed to get streaming response"
				)
			}
			setThinking(false)

			const reader = response.body.getReader()
			const decoder = new TextDecoder()
			let assistantMessageId = null

			// eslint-disable-next-line no-constant-condition
			while (true) {
				const { value, done } = await reader.read()
				if (done) break

				const chunk = decoder.decode(value)
				// Assuming NDJSON stream format from backend
				const lines = chunk
					.split("\n")
					.filter((line) => line.trim() !== "")

				for (const line of lines) {
					try {
						// Each line is a JSON object
						const parsed = JSON.parse(line)

						if (
							parsed.type === "assistantStream" ||
							parsed.type === "assistantMessage"
						) {
							const token = parsed.token || parsed.message || ""
							if (!assistantMessageId) {
								assistantMessageId =
									parsed.messageId ||
									`assistant-${Date.now()}`
							}

							setMessages((prev) => {
								const existingMsgIndex = prev.findIndex(
									(msg) => msg.id === assistantMessageId
								)
								if (existingMsgIndex !== -1) {
									const updatedMessages = [...prev]
									updatedMessages[existingMsgIndex].message +=
										token
									return updatedMessages
								} else {
									return [
										...prev,
										{
											id: assistantMessageId,
											message: token,
											isUser: false,
											type: "text"
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
			if (error.name === "AbortError") {
				console.log("Fetch aborted by user.")
			} else {
				toast.error(`Error sending message: ${error.message}`)
				console.error("Error sending message:", error)
			}
			setThinking(false)
		} finally {
			await fetchChatHistory()
		}
	}

	const clearChatHistory = async () => {
		try {
			const response = await fetch("/api/chat/clear", { method: "POST" })
			if (response.ok) {
				setMessages([])
				if (chatMode === "text") setInput("")
				toast.success("Chat history cleared.")
			} else {
				const errorData = await response.json()
				toast.error(
					`Failed to clear chat history: ${errorData.message}`
				)
			}
		} catch (error) {
			toast.error("Error clearing chat history.")
		}
	}

	// --- Effects ---
	useEffect(() => {
		fetchUserDetails()

		const getDevices = async () => {
			try {
				if (
					!navigator.mediaDevices ||
					!navigator.mediaDevices.enumerateDevices
				) {
					console.warn("enumerateDevices() not supported.")
					return
				}
				await navigator.mediaDevices.getUserMedia({
					audio: true,
					video: false
				})
				const devices = await navigator.mediaDevices.enumerateDevices()
				const audioInputDevices = devices.filter(
					(device) => device.kind === "audioinput"
				)
				if (audioInputDevices.length > 0) {
					setAudioInputDevices(
						audioInputDevices.map((d) => ({
							deviceId: d.deviceId,
							label:
								d.label ||
								`Microphone ${audioInputDevices.indexOf(d) + 1}`
						}))
					)
					if (!selectedAudioInputDevice) {
						setSelectedAudioInputDevice(
							audioInputDevices[0].deviceId
						)
					}
				}
			} catch (error) {
				toast.error(
					"Could not get microphone list. Please grant permission."
				)
			}
		}
		getDevices()

		if (chatMode === "text") {
			fetchChatHistory()
		} else {
			setIsLoading(false)
		}

		return () => {
			if (abortControllerRef.current) {
				abortControllerRef.current.abort()
			}
			if (
				backgroundCircleProviderRef.current &&
				connectionStatus !== "disconnected"
			) {
				backgroundCircleProviderRef.current.disconnect()
			}
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [])

	useEffect(() => {
		if (chatMode === "text" && chatEndRef.current) {
			chatEndRef.current.scrollIntoView({ behavior: "smooth" })
		}
	}, [messages, chatMode])

	useEffect(() => {
		if (chatMode === "text" && textareaRef.current) {
			handleInputChange({ target: textareaRef.current })
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [chatMode, input])

	// --- JSX ---
	return (
		<div className="h-screen bg-matteblack relative overflow-hidden dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<TopControlBar
				chatMode={chatMode}
				onToggleMode={handleToggleMode}
			/>
			<div className="absolute inset-0 flex flex-col justify-center items-center h-full w-full bg-matteblack z-10 pt-20">
				<div className="w-full h-full flex flex-col items-center justify-center p-5 text-white">
					{isLoading ? (
						<div className="flex justify-center items-center h-full w-full">
							<IconLoader className="w-10 h-10 text-white animate-spin" />
						</div>
					) : chatMode === "text" ? (
						<div className="w-full max-w-4xl h-full flex flex-col">
							<div className="grow overflow-y-auto p-4 rounded-xl no-scrollbar mb-4 flex flex-col gap-4">
								{messages.length === 0 && !thinking ? (
									<div className="font-Poppins h-full flex flex-col justify-center items-center text-gray-400">
										<p className="text-3xl text-white mb-4">
											Send a message to start
										</p>
									</div>
								) : (
									messages.map((msg) => (
										<div
											key={msg.id || Math.random()}
											className={`flex ${msg.isUser ? "justify-end" : "justify-start"} w-full`}
										>
											{msg.type === "tool_result" ? (
												<ToolResultBubble
													task={msg.task}
													result={msg.message}
													memoryUsed={msg.memoryUsed}
													agentsUsed={msg.agentsUsed}
													internetUsed={
														msg.internetUsed
													}
												/>
											) : (
												<ChatBubble
													message={msg.message}
													isUser={msg.isUser}
													memoryUsed={msg.memoryUsed}
													agentsUsed={msg.agentsUsed}
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
							<div className="w-full flex flex-col items-center">
								<p className="text-gray-400 font-Poppins text-xs mb-2">
									Check out our{" "}
									<a
										href="https://sentient-2.gitbook.io/docs"
										target="_blank"
										rel="noopener noreferrer"
										className="text-lightblue hover:text-lightblue/80"
									>
										docs
									</a>{" "}
									to see what Sentient can do.
								</p>
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
										<button
											onClick={sendMessage}
											disabled={
												thinking || input.trim() === ""
											}
											className="p-2 hover-button scale-100 hover:scale-110 cursor-pointer rounded-full text-white disabled:opacity-50 disabled:cursor-not-allowed"
											title="Send Message"
										>
											<IconSend className="w-4 h-4 text-white" />
										</button>
										<button
											onClick={clearChatHistory}
											className="p-2 rounded-full hover-button scale-100 cursor-pointer hover:scale-110 text-white"
											title="Clear Chat History"
										>
											<IconRefresh className="w-4 h-4 text-white" />
										</button>
									</div>
								</div>
							</div>
						</div>
					) : (
						<div className="flex flex-col items-center justify-center h-full w-full relative">
							<BackgroundCircleProvider
								ref={backgroundCircleProviderRef}
								onStatusChange={handleStatusChange}
								connectionStatusProp={connectionStatus}
							/>
							<div className="absolute inset-0 flex flex-col items-center justify-center z-20 pointer-events-none">
								<div className="flex flex-col items-center pointer-events-auto">
									{connectionStatus === "disconnected" && (
										<button
											onClick={handleStartVoice}
											className="p-4 bg-green-600 hover:bg-green-500 rounded-full text-white transition-colors duration-200 shadow-lg"
											title="Start Call"
										>
											<IconPhone size={32} />
										</button>
									)}
									{connectionStatus === "connecting" && (
										<div className="p-4 text-yellow-400">
											<IconLoader
												size={40}
												className="animate-spin"
											/>
										</div>
									)}
									{connectionStatus === "connected" && (
										<button
											onClick={handleStopVoice}
											className="p-4 bg-red-600 hover:bg-red-500 rounded-full text-white transition-colors duration-200 shadow-lg"
											title="Hang Up"
										>
											<IconPhoneOff size={32} />
										</button>
									)}
								</div>
							</div>
						</div>
					)}
				</div>
			</div>
			{!isLoading && (
				<div className="absolute bottom-6 right-6 z-30">
					<select
						value={selectedAudioInputDevice}
						onChange={handleDeviceChange}
						className="bg-neutral-700/80 backdrop-blur-sm border border-neutral-600 text-white text-xs rounded px-3 py-2 focus:outline-none focus:border-lightblue appearance-none max-w-[200px] truncate shadow-lg"
						title="Select Microphone (Restart call to apply)"
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
		</div>
	)
}

export default Chat
