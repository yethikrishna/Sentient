"use client"

import { useState, useEffect, useRef, useCallback, useMemo } from "react"
import {
	IconSend,
	IconLoader,
	IconPlayerStopFilled,
	IconBrain,
	IconWorldSearch,
	IconUsers,
	IconMapPin,
	IconFileText,
	IconArrowBackUp,
	IconX,
	IconCopy,
	IconMenu2,
	IconPhone,
	IconPhoneOff,
	IconWaveSine,
	IconMessageOff,
	IconPaperclip,
	IconFile,
	IconPlus,
	IconTools,
	IconTool,
	IconPresentation,
	IconTable,
	IconShoppingCart,
	IconCloud,
	IconChartPie,
	IconNews,
	IconBrandDiscord,
	IconBrandEvernote,
	IconBrandWhatsapp,
	IconBrandTrello,
	IconListCheck,
	IconCalendarEvent
} from "@tabler/icons-react"
import {
	IconBrandSlack,
	IconBrandNotion,
	IconBrandGithub,
	IconBrandGoogleDrive,
	IconBrandLinkedin
} from "@tabler/icons-react"
import IconGoogleMail from "@components/icons/IconGoogleMail"
import IconGoogleCalendar from "@components/icons/IconGoogleCalendar"
import IconGoogleSheets from "@components/icons/IconGoogleSheets"
import toast from "react-hot-toast"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"
import { motion, AnimatePresence } from "framer-motion"
import ChatBubble from "@components/ChatBubble"
import InteractiveNetworkBackground from "@components/ui/InteractiveNetworkBackground"
import { TextShimmer } from "@components/ui/text-shimmer"
import React from "react"
import { usePostHog } from "posthog-js/react"
import SiriSpheres from "@components/voice-visualization/SiriSpheres"
import { WebRTCClient } from "@lib/webrtc-client"
import useClickOutside from "@hooks/useClickOutside"

const toolIcons = {
	gmail: IconGoogleMail,
	gcalendar: IconGoogleCalendar,
	gsheets: IconGoogleSheets,
	gdocs: IconFileText,
	gdrive: IconBrandGoogleDrive,
	gpeople: IconUsers,
	slack: IconBrandSlack,
	notion: IconBrandNotion,
	github: IconBrandGithub,
	internet_search: IconWorldSearch,
	memory: IconBrain,
	gmaps: IconMapPin,
	linkedin: IconBrandLinkedin,
	gshopping: IconShoppingCart,
	quickchart: IconChartPie,
	google_search: IconWorldSearch,
	trello: IconBrandTrello,
	news: IconNews,
	todoist: IconListCheck, // Replacement for custom icon
	discord: IconBrandDiscord,
	evernote: IconBrandEvernote,
	whatsapp: IconBrandWhatsapp,
	gcalendar_alt: IconCalendarEvent,
	default: IconTool
// Ensure this closing brace matches the correct opening brace or remove it if unnecessary.
}
const useCasesByDomain = {
	Featured: [
		{
			title: "Overnight Updates",
			description: "Update me on overnight slack/email messages",
			prompt: "Catch me up on any important Slack messages or emails I missed overnight and summarize them for me.",
			tools: ["slack", "gmail"],
			action: "Run now"
		},
		{
			title: "Expense Analysis",
			description: "Analyze my expenses and generate a report",
			prompt: "Analyze the 'Q3 Expenses' sheet in my Google Drive and generate a summary report, highlighting the top 3 spending categories.",
			tools: ["gsheets"],
			action: "Run now"
		},
		{
			title: "Team Birthday Reminders",
			description: "Check team birthdays and send a birthday message",
			prompt: "Check my 'Team Info' Google Sheet for any birthdays today. If there is one, draft a celebratory message to post in the #general Slack channel.",
			tools: ["gsheets", "slack"],
			action: "Create workflow"
		}
	],
	Productivity: [
		{
			title: "Summarize Unread Emails",
			description: "Get a digest of your unread emails",
			prompt: "Summarize my unread emails from the last 24 hours and highlight any urgent requests.",
			tools: ["gmail"],
			action: "Run now"
		},
		{
			title: "Schedule a Meeting",
			description: "Find a time and schedule a meeting with a contact",
			prompt: "Schedule a 30-minute meeting with John Doe for tomorrow morning to discuss the Q3 report. Find a time that works for both of us.",
			tools: ["gcalendar", "gpeople"],
			action: "Run now"
		},
		{
			title: "Create a Project Brief",
			description: "Draft a new project brief in Notion",
			prompt: "Create a new page in Notion for 'Project Phoenix' with sections for Goals, Timeline, and Team Members.",
			tools: ["notion"],
			action: "Run now"
		}
	],
	Sales: [
		{
			title: "Meeting Prep",
			description: "Summarize emails & docs for an upcoming meeting",
			prompt: "I have a meeting with Acme Corp tomorrow. Summarize my recent emails with them and find the latest proposal document in Google Drive.",
			tools: ["gcalendar", "gmail", "gdrive"],
			action: "Run now"
		},
		{
			title: "Draft Follow-up Email",
			description: "Write a follow-up email after a sales call",
			prompt: "Draft a follow-up email to Jane Doe summarizing our call today and outlining the next steps we discussed.",
			tools: ["gmail", "gpeople"],
			action: "Run now"
		},
		{
			title: "Update CRM",
			description: "Log call notes and update a contact",
			prompt: "Add a note to John Smith's contact record that we discussed pricing and he is interested in the Pro plan.",
			tools: ["gpeople"],
			action: "Run now"
		}
	],
	Marketing: [
		{
			title: "Draft Campaign Email",
			description: "Write an email for a new marketing campaign",
			prompt: "Draft a marketing email to our subscribers about the new summer sale, highlighting a 20% discount.",
			tools: ["gmail"],
			action: "Run now"
		},
		{
			title: "Social Media Post Idea",
			description: "Brainstorm ideas for social media",
			prompt: "Generate 5 ideas for a tweet about our new feature launch.",
			tools: ["internet_search"],
			action: "Run now"
		},
		{
			title: "Create Campaign Brief",
			description: "Start a new campaign brief in Notion",
			prompt: "Create a new page in our Marketing workspace in Notion for the 'Q4 Holiday Campaign'.",
			tools: ["notion"],
			action: "Run now"
		}
	],
	Engineering: [
		{
			title: "Daily Standup Update",
			description: "Summarize your recent commits for standup",
			prompt: "Summarize my GitHub commits from yesterday and draft a message to post in the #engineering Slack channel for my daily update.",
			tools: ["github", "slack"],
			action: "Run now"
		},
		{
			title: "Create a New Issue",
			description: "Log a bug or feature request in GitHub",
			prompt: "Create a new issue in the 'frontend' repository titled 'Bug: Login button not working on Safari' and assign it to me.",
			tools: ["github"],
			action: "Run now"
		},
		{
			title: "Draft Technical Docs",
			description: "Start drafting new technical documentation",
			prompt: "Create a new page in our 'Engineering Wiki' in Notion to document the new API endpoint.",
			tools: ["notion"],
			action: "Run now"
		}
	]
}

const DomainSelector = ({ domains, activeDomain, onSelectDomain }) => {
	return (
		<div className="flex items-center justify-center gap-2 flex-wrap mb-8">
			{domains.map((domain) => (
				<button
					key={domain}
					onClick={() => onSelectDomain(domain)}
					className={cn(
						"px-4 py-2 rounded-full text-sm font-medium transition-colors duration-200",
						activeDomain === domain
							? "bg-white text-black shadow-lg shadow-white/10"
							: "bg-neutral-800/80 text-neutral-400 hover:bg-neutral-700/80 hover:text-white"
					)}
				>
					{domain}
				</button>
			))}
		</div>
	)
}

const UseCaseGrid = ({ useCases, onSelectPrompt }) => {
	const cardVariants = {
		hidden: { opacity: 0, y: 20 },
		visible: { opacity: 1, y: 0 }
	}

	return (
		<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			<AnimatePresence>
				{useCases.map((useCase, index) => {
					const icons = useCase.tools.map((tool) => ({
						Icon: toolIcons[tool],
						name: tool
					}))
					return (
						<motion.div
							key={useCase.title + index}
							layout
							variants={cardVariants}
							initial="hidden"
							animate="visible"
							exit="hidden"
							transition={{ duration: 0.3, delay: index * 0.05 }}
							className="bg-neutral-900/50 p-6 rounded-2xl border border-neutral-800/80 flex flex-col justify-between text-left h-full"
						>
							<div>
								<div className="flex -space-x-2 mb-4">
									{icons.map(({ Icon, name }, i) => (
										<div
											key={name + i}
											className="w-8 h-8 rounded-full flex items-center justify-center border-2 border-neutral-900 bg-white"
										>
											<Icon className="w-5 h-5" />
										</div>
									))}
								</div>
								<h3 className="font-semibold text-white mb-2">
									{useCase.title}
								</h3>
								<p className="text-neutral-400 text-sm mb-4">
									{useCase.description}
								</p>
							</div>
							<button
								onClick={() => onSelectPrompt(useCase.prompt)}
								className="text-sm font-medium text-neutral-300 hover:text-white transition-colors flex items-center gap-2"
							>
								{useCase.action}{" "}
								<span className="transition-transform group-hover:translate-x-1">
									→
								</span>
							</button>
						</motion.div>
					)
				})}
			</AnimatePresence>
		</div>
	)
}

export default function ChatPage() {
	const [displayedMessages, setDisplayedMessages] = useState([])
	const [input, setInput] = useState("")
	const [isLoading, setIsLoading] = useState(true)
	const [thinking, setThinking] = useState(false)
	const textareaRef = useRef(null)
	const chatEndRef = useRef(null)
	const abortControllerRef = useRef(null)
	const scrollContainerRef = useRef(null)
	const fileInputRef = useRef(null)

	// State for infinite scroll
	const [isLoadingOlder, setIsLoadingOlder] = useState(false)
	const [hasMoreMessages, setHasMoreMessages] = useState(true)

	// State for UI enhancements
	const [userDetails, setUserDetails] = useState(null)
	const posthog = usePostHog()
	const [isFocused, setIsFocused] = useState(false)
	const [activeDomain, setActiveDomain] = useState("Featured")
	const [replyingTo, setReplyingTo] = useState(null)
	const [isOptionsOpen, setIsOptionsOpen] = useState(false)
	const [confirmClear, setConfirmClear] = useState(false)
	const [integrations, setIntegrations] = useState([])
	const [isToolsMenuOpen, setIsToolsMenuOpen] = useState(false)
	const toolsMenuRef = useRef(null)
	const toolsButtonRef = useRef(null)

	// --- File Upload State ---
	const [selectedFile, setSelectedFile] = useState(null)
	const [isUploading, setIsUploading] = useState(false)
	const [uploadedFilename, setUploadedFilename] = useState(null)

	// --- Voice Mode State ---
	const [isVoiceMode, setIsVoiceMode] = useState(false)
	const [connectionStatus, setConnectionStatus] = useState("disconnected")
	const [audioInputDevices, setAudioInputDevices] = useState([])
	const [selectedAudioInputDevice, setSelectedAudioInputDevice] = useState("")
	const [voiceStatusText, setVoiceStatusText] = useState(
		"Click to start call"
	)
	const [statusText, setStatusText] = useState("")
	const [audioLevel, setAudioLevel] = useState(0)
	const webrtcClientRef = useRef(null)
	const ringtoneAudioRef = useRef(null)
	const connectedAudioRef = useRef(null)
	const remoteAudioRef = useRef(null)

	const fetchInitialMessages = useCallback(async () => {
		setIsLoading(true)
		try {
			const res = await fetch("/api/chat/history?limit=50")
			if (!res.ok) throw new Error("Failed to fetch messages")
			const data = await res.json()
			const fetchedMessages = data.messages || []
			setDisplayedMessages(fetchedMessages)
			setHasMoreMessages(fetchedMessages.length === 50)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	const fetchUserDetails = useCallback(async () => {
		try {
			const res = await fetch("/api/user/profile")
			if (res.ok) {
				const data = await res.json()
				setUserDetails(data)
			} else {
				setUserDetails({ given_name: "User" })
			}
		} catch (error) {
			console.error("Failed to fetch user details:", error)
			setUserDetails({ given_name: "User" })
		}
	}, [])

	useEffect(() => {
		fetchInitialMessages()
		fetchUserDetails()
		return () => {
			if (abortControllerRef.current) {
				abortControllerRef.current.abort()
			}
		}
	}, [fetchInitialMessages, fetchUserDetails])

	const fetchIntegrations = useCallback(async () => {
		try {
			const res = await fetch("/api/settings/integrations")
			if (!res.ok) throw new Error("Failed to fetch integrations")
			const data = await res.json()
			setIntegrations(data.integrations || [])
		} catch (error) {
			console.error(
				"Failed to fetch integrations for tools menu:",
				error.message
			)
		}
	}, [])

	useEffect(() => {
		fetchIntegrations()
	}, [fetchIntegrations])

	useClickOutside(toolsMenuRef, (event) => {
		if (
			toolsButtonRef.current &&
			!toolsButtonRef.current.contains(event.target)
		) {
			setIsToolsMenuOpen(false)
		}
	})

	const { connectedTools, builtinTools } = useMemo(() => {
		const hiddenTools = [
			"progress_updater",
			"chat_tools",
			"tasks",
			"google_search"
		]
		const connected = integrations.filter(
			(i) =>
				i.connected &&
				(i.auth_type === "oauth" || i.auth_type === "manual")
		)
		const builtin = integrations.filter(
			(i) => i.auth_type === "builtin" && !hiddenTools.includes(i.name)
		)
		return { connectedTools: connected, builtinTools: builtin }
	}, [integrations])

	const fetchOlderMessages = useCallback(async () => {
		if (
			isLoadingOlder ||
			!hasMoreMessages ||
			displayedMessages.length === 0
		)
			return

		setIsLoadingOlder(true)
		const oldestMessageTimestamp = displayedMessages[0].timestamp

		try {
			const res = await fetch(
				`/api/chat/history?limit=50&before_timestamp=${oldestMessageTimestamp}`
			)
			if (!res.ok) throw new Error("Failed to fetch older messages")
			const data = await res.json()

			if (data.messages && data.messages.length > 0) {
				const scrollContainer = scrollContainerRef.current
				const oldScrollHeight = scrollContainer.scrollHeight

				setDisplayedMessages((prev) => [...data.messages, ...prev])
				setHasMoreMessages(data.messages.length === 50)

				setTimeout(() => {
					scrollContainer.scrollTop =
						scrollContainer.scrollHeight - oldScrollHeight
				}, 0)
			} else {
				setHasMoreMessages(false)
			}
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoadingOlder(false)
		}
	}, [isLoadingOlder, hasMoreMessages, displayedMessages])

	useEffect(() => {
		const container = scrollContainerRef.current
		const handleScroll = () => {
			if (container && container.scrollTop === 0) {
				fetchOlderMessages()
			}
		}
		container?.addEventListener("scroll", handleScroll)
		return () => container?.removeEventListener("scroll", handleScroll)
	}, [fetchOlderMessages])

	const handleInputChange = (e) => {
		const value = e.target.value
		setInput(value)
		if (textareaRef.current) {
			textareaRef.current.style.height = "auto"
			textareaRef.current.style.height = `${Math.min(
				textareaRef.current.scrollHeight,
				200
			)}px`
		}
	}

	const handleSelectPrompt = (prompt) => {
		setInput(prompt)
		if (textareaRef.current) {
			setTimeout(() => {
				textareaRef.current.style.height = "auto"
				textareaRef.current.style.height = `${Math.min(
					textareaRef.current.scrollHeight,
					200
				)}px`
				textareaRef.current.focus()
			}, 0)
		}
	}

	const handleReply = (message) => {
		setReplyingTo(message)
		textareaRef.current?.focus()
	}

	const handleFileChange = async (event) => {
		const file = event.target.files?.[0]
		if (!file) return

		// Reset file input to allow re-uploading the same file
		event.target.value = ""

		if (file.size > 5 * 1024 * 1024) {
			// 5MB limit
			toast.error(
				"File is too large. Please select a file smaller than 5MB."
			)
			return
		}

		setSelectedFile(file)
		setIsUploading(true)
		setUploadedFilename(null)
		const toastId = toast.loading(`Uploading ${file.name}...`)

		try {
			const formData = new FormData()
			formData.append("file", file)

			const response = await fetch("/api/files/upload", {
				method: "POST",
				body: formData
			})

			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "File upload failed")
			}

			const result = await response.json()
			setUploadedFilename(result.filename)
			toast.success(`${result.filename} uploaded successfully.`, {
				id: toastId
			})
		} catch (error) {
			toast.error(`Error: ${error.message}`, { id: toastId })
			setSelectedFile(null)
		} finally {
			setIsUploading(false)
		}
	}

	const sendMessage = async () => {
		if ((!input.trim() && !uploadedFilename) || thinking || isUploading)
			return

		setThinking(true)
		abortControllerRef.current = new AbortController()

		posthog?.capture("chat_message_sent", {
			message_length: input.length,
			has_file: !!uploadedFilename
		})

		let messageContent = input.trim()
		if (uploadedFilename) {
			messageContent = `(Attached file for context: ${uploadedFilename}) ${messageContent}`
		}

		const newUserMessage = {
			id: `user-${Date.now()}`,
			role: "user",
			content: messageContent,
			timestamp: new Date().toISOString(),
			...(replyingTo && { replyToId: replyingTo.id })
		}

		setStatusText("Getting ready...")
		const updatedMessages = [...displayedMessages, newUserMessage]
		setDisplayedMessages(updatedMessages)

		setInput("")
		setReplyingTo(null)
		setUploadedFilename(null) // Reset file after sending
		setSelectedFile(null)
		if (textareaRef.current) textareaRef.current.style.height = "auto"

		try {
			const messagesToSend = updatedMessages.slice(-20).map((msg) => {
				let content = msg.content
				if (msg.replyToId) {
					const originalMsg = updatedMessages.find(
						(m) => m.id === msg.replyToId
					)
					if (originalMsg) {
						content = `<reply_to id="${originalMsg.id}">${originalMsg.content}</reply_to>\n${msg.content}`
					}
				}
				return { id: msg.id, role: msg.role, content: content }
			})

			const response = await fetch("/api/chat/message", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					messages: messagesToSend
				}),
				signal: abortControllerRef.current.signal
			})

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`)
			}

			const reader = response.body.getReader()
			const decoder = new TextDecoder()
			let assistantMessageId = `assistant-${Date.now()}`

			setDisplayedMessages((prev) => [
				...prev,
				{
					id: assistantMessageId,
					role: "assistant",
					content: "",
					timestamp: new Date().toISOString(),
					tools: []
				}
			])

			while (true) {
				const { done, value } = await reader.read()
				if (done) break

				const chunk = decoder.decode(value)
				for (const line of chunk.split("\n")) {
					if (!line.trim()) continue

					try {
						const parsed = JSON.parse(line)

						if (parsed.type === "error") {
							toast.error(`An error occurred: ${parsed.message}`)
							continue
						}

						// This is the fix: Update the temporary ID to the real one from the backend
						if (
							parsed.messageId &&
							assistantMessageId.startsWith("assistant-")
						) {
							const tempId = assistantMessageId
							assistantMessageId = parsed.messageId // Update the reference to the real ID
							setDisplayedMessages((prev) =>
								prev.map((m) =>
									m.id === tempId
										? { ...m, id: parsed.messageId }
										: m
								)
							)
						}

						// Handle status updates from the backend
						if (parsed.type === "status") {
							setStatusText(parsed.message)
							continue
						}

						// Clear status text when the actual response starts streaming
						if (parsed.type === "assistantStream" && parsed.token) {
							setStatusText("")
						}

						setDisplayedMessages((prev) =>
							prev.map((msg) => {
								if (msg.id === assistantMessageId) {
									return {
										...msg,
										content:
											msg.content + (parsed.token || ""),
										tools: parsed.tools || msg.tools
									}
								}
								return msg
							})
						)
					} catch (parseError) {
						setDisplayedMessages((prev) =>
							prev.map((msg) => {
								if (msg.id === assistantMessageId) {
									return {
										...msg,
										content: msg.content + line
									}
								}
								return msg
							})
						)
					}
				}
			}
		} catch (error) {
			if (error.name === "AbortError") {
				toast.info("Message generation stopped.")
			} else {
				toast.error(`Error: ${error.message}`)
				console.error("Fetch error:", error)
				setDisplayedMessages((prev) =>
					prev.filter((m) => m.id !== newUserMessage.id)
				)
			}
		} finally {
			setThinking(false)
			setStatusText("")
		}
	}

	const handleDeleteMessage = async (messageId) => {
		const originalMessages = [...displayedMessages]
		setDisplayedMessages((prev) => prev.filter((m) => m.id !== messageId))

		try {
			const res = await fetch("/api/chat/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ message_id: messageId })
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.error || "Failed to delete message")
			}
			toast.success("Message deleted.")
		} catch (error) {
			toast.error(error.message)
			setDisplayedMessages(originalMessages) // Revert on error
		}
	}

	const handleClearAllMessages = async () => {
		setDisplayedMessages([])
		setIsOptionsOpen(false)
		setConfirmClear(false)
		try {
			const res = await fetch("/api/chat/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ clear_all: true })
			})
			if (!res.ok) throw new Error("Failed to clear chat history")
			toast.success("Chat history cleared.")
		} catch (error) {
			toast.error(error.message)
			fetchInitialMessages() // Refetch to restore state on error
		}
	}

	const handleStopStreaming = () => {
		if (abortControllerRef.current) {
			abortControllerRef.current.abort()
			toast.info("Message generation stopped.")
		}
	}

	useEffect(() => {
		if (chatEndRef.current) {
			chatEndRef.current.scrollIntoView({ behavior: "smooth" })
		}
	}, [displayedMessages, thinking])

	const getGreeting = () => {
		const hour = new Date().getHours()
		if (hour < 12) return "Good Morning"
		if (hour < 18) return "Good Afternoon"
		return "Good Evening"
	}

	const getFinalAnswer = (content) => {
		if (!content || typeof content !== "string") return ""

		const answerParts = []
		const regex =
			/(<think>[\s\S]*?<\/think>|<tool_code[^>]*>[\s\S]*?<\/tool_code>|<tool_result[^>]*>[\s\S]*?<\/tool_result>|<answer>[\s\S]*?<\/answer>)/g
		let lastIndex = 0
		let inToolCallPhase = false

		for (const match of content.matchAll(regex)) {
			const precedingText = content.substring(lastIndex, match.index)
			if (precedingText.trim() && !inToolCallPhase) {
				answerParts.push(precedingText.trim())
			}

			const tag = match[0]
			if (tag.startsWith("<tool_code")) inToolCallPhase = true
			else if (tag.startsWith("<tool_result")) inToolCallPhase = false
			else if (tag.startsWith("<answer>")) {
				const answerContent =
					tag.match(/<answer>([\s\S]*?)<\/answer>/)?.[1] || ""
				if (answerContent) answerParts.push(answerContent.trim())
			}
			lastIndex = match.index + tag.length
		}
		const remainingText = content.substring(lastIndex)
		if (remainingText.trim() && !inToolCallPhase) {
			answerParts.push(remainingText.trim())
		}

		const plainText = answerParts.join("\n\n")
		if (plainText) return plainText
		return content.replace(/<[^>]+>/g, "").trim()
	}

	// --- Voice Mode Handlers ---
	const handleStatusChange = useCallback((status) => {
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
					.catch((e) => console.error("Error playing sound:", e))
			}
			setVoiceStatusText("Listening...")
		} else if (status === "disconnected") {
			setVoiceStatusText("Click to start call")
		} else if (status === "connecting") {
			setVoiceStatusText("Connecting...")
		}
	}, [])

	const handleVoiceEvent = useCallback((event) => {
		if (event.type === "stt_result" && event.text) {
			setDisplayedMessages((prev) => [
				...prev,
				{
					id: `user_${Date.now()}`,
					role: "user",
					content: event.text,
					timestamp: new Date().toISOString()
				}
			])
		} else if (event.type === "llm_result" && event.text) {
			setDisplayedMessages((prev) => [
				...prev,
				{
					id: event.messageId || `assistant_${Date.now()}`,
					role: "assistant",
					content: event.text,
					timestamp: new Date().toISOString()
				}
			])
		} else if (event.type === "status") {
			if (event.message === "thinking") setVoiceStatusText("Thinking...")
			else if (event.message === "speaking")
				setVoiceStatusText("Speaking...")
			else if (event.message === "listening")
				setVoiceStatusText("Listening...")
			else if (event.message === "transcribing")
				setVoiceStatusText("Transcribing...")
			else if (event.message === "choosing_tools")
				setVoiceStatusText("Choosing tools...")
			else if (event.message && event.message.startsWith("using_tool_")) {
				const toolName = event.message
					.replace("using_tool_", "")
					.replace("_server", "")
					.replace("_mcp", "")
				setVoiceStatusText(
					`Using ${
						toolName.charAt(0).toUpperCase() + toolName.slice(1)
					}...`
				)
			}
		} else if (event.type === "error") {
			toast.error(`Voice Error: ${event.message}`)
			setVoiceStatusText("Error. Click to retry.")
		}
	}, [])

	const handleAudioLevel = useCallback((level) => {
		setAudioLevel((prev) => prev * 0.7 + level * 0.3)
	}, [])

	const handleStartVoice = async () => {
		if (connectionStatus !== "disconnected") return

		setConnectionStatus("connecting")
		setVoiceStatusText("Connecting...")
		try {
			// Step 1: Get the main auth token
			const tokenResponse = await fetch("/api/auth/token")
			if (!tokenResponse.ok) throw new Error("Could not get auth token.")
			const { accessToken } = await tokenResponse.json()

			// Step 2: Use the auth token to get a temporary RTC token
			const serverUrl =
				process.env.NEXT_PUBLIC_APP_SERVER_URL ||
				"http://localhost:5000"
			const rtcTokenResponse = await fetch(
				`${serverUrl}/voice/initiate`,
				{
					method: "POST",
					headers: {
						Authorization: `Bearer ${accessToken}`
					}
				}
			)
			if (!rtcTokenResponse.ok)
				throw new Error("Could not initiate voice session.")
			const { rtc_token } = await rtcTokenResponse.json()

			// Step 3: Create and connect WebRTCClient directly
			if (webrtcClientRef.current) {
				webrtcClientRef.current.disconnect()
			}
			const client = new WebRTCClient({
				onConnected: () => handleStatusChange("connected"),
				onDisconnected: () => handleStatusChange("disconnected"),
				onAudioStream: (stream) => {
					if (remoteAudioRef.current) {
						console.log(
							"Received remote audio stream, attaching to audio element."
						)
						remoteAudioRef.current.srcObject = stream
						remoteAudioRef.current
							.play()
							.catch((e) =>
								console.error("Error playing remote audio:", e)
							)
					}
				},
				onAudioLevel: handleAudioLevel,
				onEvent: handleVoiceEvent
			})
			webrtcClientRef.current = client

			// Step 3: Play ringing and connect
			if (ringtoneAudioRef.current) {
				ringtoneAudioRef.current.volume = 0.3
				ringtoneAudioRef.current.loop = true
				ringtoneAudioRef.current
					.play()
					.catch((e) => console.error("Error playing ringtone:", e))
			}
			await webrtcClientRef.current.connect(
				selectedAudioInputDevice,
				accessToken,
				rtc_token
			)
		} catch (error) {
			toast.error(
				`Failed to connect: ${error.message || "Unknown error"}`
			)
			handleStatusChange("disconnected")
		}
	}

	const handleStopVoice = () => {
		if (connectionStatus === "disconnected" || !webrtcClientRef.current) {
			return
		}

		webrtcClientRef.current?.disconnect()

		// 2. Immediately stop any playing audio.
		if (ringtoneAudioRef.current) {
			ringtoneAudioRef.current.pause()
			ringtoneAudioRef.current.currentTime = 0
		}
		if (connectedAudioRef.current) {
			connectedAudioRef.current.pause()
			connectedAudioRef.current.currentTime = 0
		}

		// 3. Force the UI state back to disconnected immediately.
		setConnectionStatus("disconnected")
		setVoiceStatusText("Click to start call")
	}

	const toggleVoiceMode = () => {
		if (isVoiceMode) {
			handleStopVoice()
		}
		setIsVoiceMode(!isVoiceMode)
	}

	useEffect(() => {
		const getDevices = async () => {
			try {
				if (
					!navigator.mediaDevices ||
					!navigator.mediaDevices.enumerateDevices
				)
					return
				await navigator.mediaDevices.getUserMedia({
					audio: {
						noiseSuppression: false,
						echoCancellation: false
					},
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
			// This cleanup now only runs when the ChatPage component unmounts
			if (webrtcClientRef.current) {
				webrtcClientRef.current.disconnect()
			}
		}
	}, [selectedAudioInputDevice])

	const renderReplyPreview = () => (
		<AnimatePresence>
			{replyingTo && (
				<motion.div
					initial={{ opacity: 0, y: 10 }}
					animate={{ opacity: 1, y: 0 }}
					exit={{ opacity: 0, y: 10 }}
					className="bg-neutral-800/60 p-3 rounded-t-lg border-b border-neutral-700/50 flex justify-between items-center"
				>
					<div>
						<p className="text-xs text-neutral-400 flex items-center gap-1.5">
							<IconArrowBackUp size={14} /> Replying to{" "}
							{replyingTo.role === "user"
								? "yourself"
								: "the assistant"}
						</p>
						<p className="text-sm text-neutral-200 mt-1 truncate">
							{getFinalAnswer(replyingTo.content)}
						</p>
					</div>
					<button
						onClick={() => setReplyingTo(null)}
						className="p-1.5 rounded-full text-neutral-400 hover:bg-neutral-700 hover:text-white"
					>
						<IconX size={16} />
					</button>
				</motion.div>
			)}
		</AnimatePresence>
	)

	const renderUploadedFilePreview = () => (
		<AnimatePresence>
			{uploadedFilename && (
				<motion.div
					initial={{ opacity: 0, y: 10 }}
					animate={{ opacity: 1, y: 0 }}
					exit={{ opacity: 0, y: 10 }}
					className="bg-neutral-800/60 p-3 rounded-t-lg border-b border-neutral-700/50 flex justify-between items-center"
				>
					<div className="flex items-center gap-2 overflow-hidden">
						<IconFile
							size={16}
							className="text-neutral-400 flex-shrink-0"
						/>
						<p
							className="text-sm text-neutral-200 truncate"
							title={uploadedFilename}
						>
							{uploadedFilename}
						</p>
					</div>
					<button
						onClick={() => {
							setUploadedFilename(null)
							setSelectedFile(null)
						}}
						className="p-1.5 rounded-full text-neutral-400 hover:bg-neutral-700 hover:text-white"
					>
						<IconX size={16} />
					</button>
				</motion.div>
			)}
		</AnimatePresence>
	)

	const renderInputArea = () => (
		<div className="relative bg-neutral-800/60 backdrop-blur-sm border border-neutral-700/50 rounded-2xl">
			<div className="p-4 flex items-start gap-4">
				<textarea
					ref={textareaRef}
					value={input}
					onChange={handleInputChange}
					onFocus={() => setIsFocused(true)}
					onBlur={() => setIsFocused(false)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && !e.shiftKey) {
							e.preventDefault()
							sendMessage()
						}
					}}
					placeholder="Type a message, or attach a file..."
					className="w-full p-4 pl-14 pr-24 bg-transparent text-base text-white placeholder-neutral-500 resize-none focus:ring-0 focus:outline-none overflow-y-auto custom-scrollbar"
					rows={1}
					style={{ maxHeight: "200px" }}
				/>
				<div className="absolute left-3 bottom-3 flex items-center gap-2">
					<input
						type="file"
						ref={fileInputRef}
						onChange={handleFileChange}
						className="hidden"
					/>
					<button
						onClick={() => fileInputRef.current?.click()}
						disabled={isUploading}
						className="p-2.5 rounded-full text-white bg-neutral-700 hover:bg-neutral-600 transition-colors disabled:opacity-50"
						data-tooltip-id="home-tooltip"
						data-tooltip-content="Attach File (Max 5MB)"
					>
						{isUploading ? (
							<IconLoader size={18} className="animate-spin" />
						) : (
							<IconPaperclip size={18} />
						)}
					</button>
				</div>
				<div className="absolute right-3 bottom-3 flex items-center gap-2">
					<button
						onClick={toggleVoiceMode}
						className="p-2.5 rounded-full text-white bg-neutral-700 hover:bg-neutral-600 transition-colors"
						data-tooltip-id="home-tooltip"
						data-tooltip-content="Switch to Voice Mode"
					>
						<IconWaveSine size={18} />
					</button>
					{thinking ? (
						<button
							onClick={handleStopStreaming}
							className="p-2.5 rounded-full text-white bg-red-600 hover:bg-red-500"
							data-tooltip-id="home-tooltip"
							data-tooltip-content="Stop Generation"
						>
							<IconPlayerStopFilled size={18} />
						</button>
					) : (
						<button
							onClick={sendMessage}
							disabled={
								(!input.trim() && !uploadedFilename) ||
								thinking ||
								isUploading
							}
							className="p-2.5 bg-brand-orange rounded-full text-white disabled:opacity-50 hover:bg-brand-orange/90 transition-all shadow-md"
						>
							<IconSend size={18} />
						</button>
					)}
				</div>
			</div>
		</div>
	)

	const renderToolsMenu = () => (
		<AnimatePresence>
			{isToolsMenuOpen && (
				<motion.div
					ref={toolsMenuRef}
					initial={{ opacity: 0, y: 10, scale: 0.95 }}
					animate={{ opacity: 1, y: 0, scale: 1 }}
					exit={{ opacity: 0, y: 10, scale: 0.95 }}
					transition={{ duration: 0.2, ease: "easeInOut" }}
					className="absolute bottom-full mb-2 w-full max-w-sm bg-neutral-900/90 backdrop-blur-md border border-neutral-700 rounded-xl shadow-lg p-3 z-50"
				>
					<div className="max-h-72 overflow-y-auto custom-scrollbar pr-2">
						{connectedTools.length > 0 && (
							<div className="mb-3">
								<p className="text-xs text-neutral-400 font-semibold mb-2 px-2">
									Connected Apps
								</p>
								<div className="space-y-1">
									{connectedTools.map((tool) => {
										const Icon =
											toolIcons[tool.name] ||
											toolIcons.default
										return (
											<div
												key={tool.name}
												className="flex items-center gap-3 p-2 rounded-md"
											>
												<Icon className="w-5 h-5 text-neutral-300 flex-shrink-0" />
												<span className="text-sm text-neutral-200 font-medium">
													{tool.display_name}
												</span>
											</div>
										)
									})}
								</div>
							</div>
						)}
						{builtinTools.length > 0 && (
							<div>
								<p className="text-xs text-neutral-400 font-semibold mb-2 px-2">
									Built-in Tools
								</p>
								<div className="space-y-1">
									{builtinTools.map((tool) => {
										const Icon =
											toolIcons[tool.name] ||
											toolIcons.default
										return (
											<div
												key={tool.name}
												className="flex items-center gap-3 p-2 rounded-md"
											>
												<Icon className="w-5 h-5 text-neutral-300 flex-shrink-0" />
												<span className="text-sm text-neutral-200 font-medium">
													{tool.display_name}
												</span>
											</div>
										)
									})}
								</div>
							</div>
						)}
					</div>
				</motion.div>
			)}
		</AnimatePresence>
	)

	const renderOptionsMenu = () => (
		<div className="absolute top-6 right-6 z-30">
			<div className="relative">
				<button
					onClick={() => {
						setIsOptionsOpen(!isOptionsOpen)
						setConfirmClear(false) // Reset confirmation on toggle
					}}
					className="p-2 rounded-full bg-neutral-800/50 hover:bg-neutral-700/80 text-white"
				>
					<IconMenu2 size={20} />
				</button>
				<AnimatePresence>
					{isOptionsOpen && (
						<motion.div
							initial={{ opacity: 0, y: 10, scale: 0.95 }}
							animate={{ opacity: 1, y: 0, scale: 1 }}
							exit={{ opacity: 0, y: 10, scale: 0.95 }}
							className="absolute top-full right-0 mt-2 w-48 bg-neutral-900/80 backdrop-blur-md border border-neutral-700 rounded-lg shadow-lg p-1"
						>
							<button
								onClick={() => {
									if (confirmClear) {
										handleClearAllMessages()
									} else {
										setConfirmClear(true)
									}
								}}
								className={cn(
									"w-full text-left px-3 py-2 text-sm rounded-md transition-colors",
									confirmClear
										? "bg-red-600/80 text-white hover:bg-red-500"
										: "text-neutral-300 hover:bg-neutral-700/50"
								)}
							>
								{confirmClear ? "Confirm Clear?" : "Clear Chat"}
							</button>
						</motion.div>
					)}
				</AnimatePresence>
			</div>
		</div>
	)

	return (
		<div className="flex-1 flex h-screen text-white overflow-hidden">
			<Tooltip id="home-tooltip" place="right" style={{ zIndex: 9999 }} />
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
			<audio ref={remoteAudioRef} autoPlay playsInline />
			{displayedMessages.length > 0 &&
				!isVoiceMode &&
				renderOptionsMenu()}
			<div className="flex-1 flex flex-col overflow-hidden relative w-full pb-16 md:pb-0">
				<div className="absolute inset-0 z-[-1] network-grid-background">
					<InteractiveNetworkBackground />
				</div>
				<div className="absolute -top-[250px] left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-brand-orange/10 rounded-full blur-3xl -z-10" />

				<main
					ref={scrollContainerRef}
					className="flex-1 overflow-y-auto p-6 flex flex-col custom-scrollbar"
				>
					{isLoading ? (
						<div className="flex-1 flex justify-center items-center">
							<IconLoader className="animate-spin text-neutral-500" />
						</div>
					) : isVoiceMode ? (
						<div className="flex-1 flex flex-col relative overflow-hidden">
							{/* The 3D visualization will render here as a background */}
							<SiriSpheres
								status={connectionStatus}
								audioLevel={audioLevel}
							/>

							{/* Overlay for controls, status, and messages */}
							<div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-4">
								{/* Call control buttons */}
								<div className="mb-8">
									<AnimatePresence mode="wait">
										<motion.div
											key={connectionStatus}
											initial={{ opacity: 0, scale: 0.8 }}
											animate={{ opacity: 1, scale: 1 }}
											exit={{ opacity: 0, scale: 0.8 }}
										>
											{connectionStatus ===
											"disconnected" ? (
												<button
													onClick={handleStartVoice}
													className="flex h-24 w-24 items-center justify-center rounded-full bg-green-600 text-white shadow-lg transition-colors duration-200 hover:bg-green-500"
													title="Start Call"
												>
													<IconPhone size={36} />
												</button>
											) : connectionStatus ===
											  "connecting" ? (
												<div className="flex h-24 w-24 items-center justify-center rounded-full bg-yellow-600 text-white shadow-lg">
													<IconLoader
														size={36}
														className="animate-spin"
													/>
												</div>
											) : (
												<button
													onClick={handleStopVoice}
													className="flex h-24 w-24 items-center justify-center rounded-full bg-red-600 text-white shadow-lg transition-colors duration-200 hover:bg-red-500"
													title="Hang Up"
												>
													<IconPhoneOff size={36} />
												</button>
											)}
										</motion.div>
									</AnimatePresence>
								</div>

								{/* Status and Message Display */}
								<div className="text-center space-y-4 max-w-2xl">
									<div className="text-lg font-medium text-gray-300 min-h-[24px]">
										<AnimatePresence mode="wait">
											<motion.div
												key={voiceStatusText}
												initial={{ opacity: 0, y: 10 }}
												animate={{ opacity: 1, y: 0 }}
												exit={{ opacity: 0, y: -10 }}
												transition={{ duration: 0.2 }}
											>
												<TextShimmer className="font-mono text-base">
													{voiceStatusText}
												</TextShimmer>
											</motion.div>
										</AnimatePresence>
									</div>
									<div className="text-2xl font-semibold text-white min-h-[64px]">
										<AnimatePresence mode="wait">
											{displayedMessages
												.filter(
													(m) => m.role === "user"
												)
												.slice(-1)
												.map((msg) => (
													<motion.div
														key={msg.id}
														initial={{
															opacity: 0,
															y: 15
														}}
														animate={{
															opacity: 1,
															y: 0
														}}
														exit={{
															opacity: 0,
															y: -15
														}}
														transition={{
															duration: 0.3
														}}
													>
														{getFinalAnswer(
															msg.content
														)}
													</motion.div>
												))}
										</AnimatePresence>
									</div>
								</div>
							</div>
						</div>
					) : displayedMessages.length === 0 && !thinking ? (
						<div className="flex-1 flex flex-col justify-center items-center p-6 text-center">
							<div>
								<h1 className="text-4xl sm:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-100 to-neutral-400 py-4">
									{getGreeting()},{" "}
									{userDetails?.given_name || "User"}
								</h1>
								<p className="mt-2 text-lg text-neutral-400">
									How can I help you today?
								</p>
							</div>
							<div className="w-full max-w-4xl mx-auto mt-12 ">
								<div className="relative">
									{renderToolsMenu()}
									{renderInputArea()}
								</div>
								<div className="mt-12">
									<DomainSelector
										domains={Object.keys(useCasesByDomain)}
										activeDomain={activeDomain}
										onSelectDomain={setActiveDomain}
									/>
									<UseCaseGrid
										key={activeDomain}
										useCases={
											useCasesByDomain[activeDomain]
										}
										onSelectPrompt={handleSelectPrompt}
									/>
								</div>
							</div>
						</div>
					) : (
						<div className="w-full max-w-4xl mx-auto flex flex-col gap-4 flex-1">
							{isLoadingOlder && (
								<div className="flex justify-center py-4">
									<IconLoader className="animate-spin text-neutral-500" />
								</div>
							)}
							{displayedMessages.map((msg, i) => (
								<div
									key={msg.id || i}
									className={cn(
										"flex w-full",
										msg.role === "user"
											? "justify-end"
											: "justify-start"
									)}
								>
									<ChatBubble
										role={msg.role}
										content={msg.content}
										tools={msg.tools || []}
										onReply={handleReply}
										message={msg}
										allMessages={displayedMessages}
										onDelete={handleDeleteMessage}
									/>
								</div>
							))}
							<div className="flex w-full justify-start">
								<AnimatePresence>
									{thinking && (
										<motion.div
											initial={{ opacity: 0, y: 10 }}
											animate={{ opacity: 1, y: 0 }}
											exit={{ opacity: 0, y: 10 }}
											className="flex items-center gap-2 p-3 bg-neutral-800/50 backdrop-blur-sm rounded-2xl self-start"
										>
											<TextShimmer
												className="font-mono text-sm"
												duration={1.5}
											>
												{statusText || "Thinking..."}
											</TextShimmer>
										</motion.div>
									)}
								</AnimatePresence>
							</div>
							<div ref={chatEndRef} />
						</div>
					)}
				</main>
				{!isLoading && !isVoiceMode && displayedMessages.length > 0 && (
					<div className="px-4 pt-2 pb-4 sm:px-6 sm:pb-6 bg-transparent">
						<div className="w-full max-w-4xl mx-auto">
							{uploadedFilename
								? renderUploadedFilePreview()
									: renderReplyPreview()}
							{renderToolsMenu()}
							{renderInputArea()}
						</div>
					</div>
				)}
				{isVoiceMode && (
					<div className="absolute bottom-6 right-6 z-30 flex items-center gap-2">
						<button
							onClick={toggleVoiceMode}
							className="p-2.5 rounded-full bg-neutral-700/80 backdrop-blur-sm hover:bg-blue-500 text-white shadow-lg"
							title="Switch to Text Mode"
						>
							<IconMessageOff size={18} />
						</button>
						<select
							value={selectedAudioInputDevice}
							onChange={(e) =>
								setSelectedAudioInputDevice(e.target.value)
							}
							className="bg-neutral-700/80 backdrop-blur-sm border border-neutral-600 text-white text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 appearance-none max-w-[200px] truncate shadow-lg"
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
					</div>
				)}
			</div>
		</div>
	)
}
