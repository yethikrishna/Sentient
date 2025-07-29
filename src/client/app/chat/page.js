"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import {
	IconSend,
	IconLoader,
	IconPlayerStopFilled,
	IconBrain,
	IconWorldSearch,
	IconUsers,
	IconMapPin,
	IconFileText
} from "@tabler/icons-react"
import {
	IconBrandSlack,
	IconBrandNotion,
	IconBrandGithub,
	IconBrandGoogleDrive
} from "@tabler/icons-react"
import IconGoogleMail from "@components/icons/IconGoogleMail"
import IconGoogleCalendar from "@components/icons/IconGoogleCalendar"
import IconGoogleSheets from "@components/icons/IconGoogleSheets"
import toast from "react-hot-toast"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"
import { motion, AnimatePresence } from "framer-motion"
import ChatBubble from "@components/ChatBubble"
import React from "react"
import { usePostHog } from "posthog-js/react"

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
	gmaps: IconMapPin
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
	const [messages, setMessages] = useState([])
	const [input, setInput] = useState("")
	const [isLoading, setIsLoading] = useState(true)
	const [thinking, setThinking] = useState(false)
	const textareaRef = useRef(null)
	const chatEndRef = useRef(null)
	const abortControllerRef = useRef(null)
	const scrollContainerRef = useRef(null)

	// State for infinite scroll
	const [isLoadingOlder, setIsLoadingOlder] = useState(false)
	const [hasMoreMessages, setHasMoreMessages] = useState(true)

	// State for UI enhancements from old page
	const [userDetails, setUserDetails] = useState(null)
	const posthog = usePostHog()
	const [isFocused, setIsFocused] = useState(false)
	const [activeDomain, setActiveDomain] = useState("Featured")

	const fetchInitialMessages = useCallback(async () => {
		setIsLoading(true)
		try {
			const res = await fetch("/api/chat/history?limit=50")
			if (!res.ok) throw new Error("Failed to fetch messages")
			const data = await res.json()
			const fetchedMessages = data.messages || []
			setMessages(fetchedMessages)
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

	const fetchOlderMessages = useCallback(async () => {
		if (isLoadingOlder || !hasMoreMessages || messages.length === 0) return

		setIsLoadingOlder(true)
		const oldestMessageTimestamp = messages[0].timestamp

		try {
			const res = await fetch(
				`/api/chat/history?limit=50&before_timestamp=${oldestMessageTimestamp}`
			)
			if (!res.ok) throw new Error("Failed to fetch older messages")
			const data = await res.json()

			if (data.messages && data.messages.length > 0) {
				const scrollContainer = scrollContainerRef.current
				const oldScrollHeight = scrollContainer.scrollHeight

				setMessages((prev) => [...data.messages, ...prev])
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
	}, [isLoadingOlder, hasMoreMessages, messages])

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

	const sendMessage = async () => {
		if (input.trim() === "") return
		posthog?.capture("chat_message_sent", {
			message_length: input.length
		})

		const newUserMessage = {
			id: `user-${Date.now()}`,
			role: "user",
			content: input.trim(),
			timestamp: new Date().toISOString()
		}

		const updatedMessages = [...messages, newUserMessage]
		setMessages(updatedMessages)
		setInput("")
		if (textareaRef.current) textareaRef.current.style.height = "auto"
		setThinking(true)

		abortControllerRef.current = new AbortController()

		const processStream = async () => {
			try {
				const apiMessages = updatedMessages.map((msg) => ({
					role: msg.role,
					content: msg.content
				}))

				const response = await fetch("/api/chat/message", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						messages: apiMessages
					}),
					signal: abortControllerRef.current.signal
				})

				if (!response.ok) {
					throw new Error(`HTTP error! status: ${response.status}`)
				}

				const reader = response.body.getReader()
				const decoder = new TextDecoder()
				let assistantMessageId = `assistant-${Date.now()}`

				setMessages((prev) => [
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
								toast.error(
									`An error occurred: ${parsed.message}`
								)
								continue
							}

							setMessages((prev) =>
								prev.map((msg) => {
									if (msg.id === assistantMessageId) {
										return {
											...msg,
											content:
												msg.content +
												(parsed.token || ""),
											tools: parsed.tools || msg.tools
										}
									}
									return msg
								})
							)
						} catch (parseError) {
							setMessages((prev) =>
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
				}
			} finally {
				setThinking(false)
			}
		}

		processStream()
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
	}, [messages, thinking])

	const getGreeting = () => {
		const hour = new Date().getHours()
		if (hour < 12) return "Good Morning"
		if (hour < 18) return "Good Afternoon"
		return "Good Evening"
	}

	const renderInputArea = () => (
		<div
			className={cn(
				"rounded-2xl shadow-2xl shadow-black/40",
				!isFocused &&
					"p-0.5 bg-gradient-to-tr from-blue-500 to-cyan-500"
			)}
		>
			<div className="relative bg-neutral-900 rounded-[15px] flex items-end">
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
					placeholder="Ask me anything..."
					className="w-full p-4 pr-24 bg-transparent text-base text-white placeholder-neutral-500 resize-none focus:ring-0 focus:outline-none overflow-y-auto custom-scrollbar"
					rows={1}
					style={{ maxHeight: "200px" }}
				/>
				<div className="absolute right-3 bottom-3 flex items-center gap-2">
					{thinking ? (
						<button
							onClick={handleStopStreaming}
							className="p-2.5 rounded-full text-white bg-red-600 hover:bg-red-500 transition-colors"
							data-tooltip-id="home-tooltip"
							data-tooltip-content="Stop Generation"
						>
							<IconPlayerStopFilled size={18} />
						</button>
					) : (
						<button
							onClick={sendMessage}
							disabled={!input.trim()}
							className="p-2.5 bg-gradient-to-tr from-blue-500 to-cyan-500 rounded-full text-white disabled:opacity-50 hover:from-blue-400 hover:to-cyan-400 transition-all shadow-md"
						>
							<IconSend size={18} />
						</button>
					)}
				</div>
			</div>
		</div>
	)

	return (
		<div className="flex-1 flex bg-black text-white overflow-hidden md:pl-20">
			<Tooltip id="home-tooltip" place="right" style={{ zIndex: 9999 }} />
			<div className="flex flex-col flex-1 relative bg-black pb-16 md:pb-0">
				{messages.length === 0 && (
					<div className="absolute inset-0 h-full w-full bg-gradient-to-br from-neutral-900 to-black bg-[linear-gradient(110deg,#09090b,45%,#1e293b,55%,#09090b)] bg-[length:200%_100%] animate-shimmer" />
				)}

				<main
					ref={scrollContainerRef}
					className="flex-1 overflow-y-auto p-6 flex flex-col custom-scrollbar z-10"
				>
					{isLoading ? (
						<div className="flex-1 flex justify-center items-center">
							<IconLoader className="animate-spin text-neutral-500" />
						</div>
					) : messages.length === 0 && !thinking ? (
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
							<div className="w-full max-w-4xl mx-auto mt-12">
								{renderInputArea()}
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
							{messages.map((msg, i) => (
								<div
									key={msg.id || i}
									className={cn(
										"flex",
										msg.role === "user"
											? "justify-end"
											: "justify-start"
									)}
								>
									<ChatBubble
										role={msg.role}
										content={msg.content}
										tools={msg.tools || []}
									/>
								</div>
							))}
							<AnimatePresence>
								{thinking && (
									<motion.div
										initial={{ opacity: 0, y: 10 }}
										animate={{ opacity: 1, y: 0 }}
										exit={{ opacity: 0 }}
										className="flex items-center gap-2 p-3 bg-neutral-800 rounded-lg self-start"
									>
										<div className="bg-neutral-500 rounded-full h-2 w-2 animate-pulse delay-75"></div>
										<div className="bg-neutral-500 rounded-full h-2 w-2 animate-pulse delay-150"></div>
										<div className="bg-neutral-500 rounded-full h-2 w-2 animate-pulse delay-300"></div>
									</motion.div>
								)}
							</AnimatePresence>
							<div ref={chatEndRef} />
						</div>
					)}
				</main>
				{!isLoading && messages.length > 0 && (
					<div className="px-4 pt-2 pb-4 sm:px-6 sm:pb-6 bg-black border-t border-neutral-800/50">
						<div className="w-full max-w-4xl mx-auto">
							{renderInputArea()}
						</div>
					</div>
				)}
			</div>
		</div>
	)
}
