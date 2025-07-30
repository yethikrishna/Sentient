// src/client/app/chat/[[...chatId]]/page.js
"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
	IconSend,
	IconLoader,
	IconPlayerStopFilled,
	IconPlus,
	IconTrash,
	IconMessage,
	IconBrain,
	IconWorldSearch,
	IconUsers,
	IconLayoutSidebarLeftCollapse,
	IconLayoutSidebarLeftExpand,
	IconMapPin
} from "@tabler/icons-react"
import {
	IconBrandSlack,
	IconBrandNotion,
	IconBrandGithub,
	IconBrandGoogleDrive,
	IconFileText
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

const ChatHistorySidebar = ({
	chatList,
	activeChatId,
	onSelectChat,
	onNewChat,
	onDeleteChat,
	isLoading,
	isSidebarOpen,
	onClose
}) => {
	return (
		<motion.div
			initial={false}
			animate={{ width: isSidebarOpen ? 280 : 0 }}
			transition={{ type: "spring", stiffness: 400, damping: 40 }}
			className="bg-neutral-900/50 flex flex-col h-full border-r border-[var(--color-primary-surface)] flex-shrink-0 overflow-hidden"
		>
			<div className="w-[280px] h-full flex flex-col">
				<div className="flex items-center justify-between p-4 border-b border-[var(--color-primary-surface)]">
					<h3 className="font-semibold text-white text-lg">
						Conversations
					</h3>
				</div>
				<div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1.5">
					{isLoading ? (
						<div className="flex justify-center items-center h-full">
							<IconLoader className="animate-spin text-neutral-500" />
						</div>
					) : (
						chatList.map((chat) => (
							<div
								key={chat.chat_id}
								className="relative group w-full"
							>
								<button
									onClick={() => onSelectChat(chat.chat_id)}
									className={cn(
										"w-full text-left p-3 rounded-lg transition-colors text-sm flex items-center gap-3",
										activeChatId === chat.chat_id
											? "bg-[var(--color-accent-blue)] text-white font-medium"
											: "text-neutral-300 hover:bg-neutral-700/50"
									)}
								>
									<IconMessage
										size={18}
										className="flex-shrink-0"
									/>
									<span className="truncate flex-1">
										{chat.title}
									</span>
								</button>
								{activeChatId === chat.chat_id && (
									<button
										onClick={(e) => {
											e.stopPropagation()
											onDeleteChat(chat.chat_id)
										}}
										className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-neutral-400 hover:text-red-400 hover:bg-black/20 rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
									>
										<IconTrash size={14} />
									</button>
								)}
							</div>
						))
					)}
				</div>
			</div>
		</motion.div>
	)
}

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
									���
								</span>
							</button>
						</motion.div>
					)
				})}
			</AnimatePresence>
		</div>
	)
}

export default function ChatPage({ params }) {
	const router = useRouter()
	const urlChatId = params.chatId ? params.chatId[0] : null

	const [activeChatId, setActiveChatId] = useState(urlChatId)
	const [isHistoryOpen, setIsHistoryOpen] = useState(false)
	const [activeDomain, setActiveDomain] = useState("Featured")
	const [chatList, setChatList] = useState([])
	const [messages, setMessages] = useState([])
	const [input, setInput] = useState("")
	const [isLoadingHistory, setIsLoadingHistory] = useState(true)
	const [isLoadingMessages, setIsLoadingMessages] = useState(false)
	const [thinking, setThinking] = useState(false)
	const textareaRef = useRef(null)
	const chatEndRef = useRef(null)
	const abortControllerRef = useRef(null)
	const scrollContainerRef = useRef(null)
	const [userDetails, setUserDetails] = useState(null)
	const posthog = usePostHog()
	const [isFocused, setIsFocused] = useState(false)

	useEffect(() => {
		setActiveChatId(urlChatId)
	}, [urlChatId])

	const fetchHistory = useCallback(async () => {
		setIsLoadingHistory(true)
		try {
			const res = await fetch("/api/chat/history")
			if (!res.ok) throw new Error("Failed to fetch chat history")
			const data = await res.json()
			setChatList(data.chats || [])
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoadingHistory(false)
		}
	}, [])

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/data")
			if (!response.ok) throw new Error("Failed to fetch user details")
			const result = await response.json()
			const userName =
				result?.data?.personalInfo?.name ||
				result?.data?.onboardingAnswers?.["user-name"]
			setUserDetails({ given_name: userName || "User" })
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
			setUserDetails({ given_name: "User" })
		}
	}, [])

	useEffect(() => {
		fetchHistory()
		fetchUserDetails()
		return () => {
			if (abortControllerRef.current) {
				abortControllerRef.current.abort()
			}
		}
	}, [fetchHistory, fetchUserDetails])

	useEffect(() => {
		const fetchMessages = async () => {
			if (!activeChatId) {
				setMessages([])
				return
			}
			setIsLoadingMessages(true)
			try {
				const res = await fetch(`/api/chat/history/${activeChatId}`)
				if (!res.ok) throw new Error("Failed to fetch messages")
				const data = await res.json()
				setMessages(data.messages || [])
			} catch (error) {
				toast.error(error.message)
			} finally {
				setIsLoadingMessages(false)
			}
		}
		fetchMessages()
	}, [activeChatId])

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
			role: "user",
			content: input,
			id: Date.now()
		}

		const updatedMessages = [...messages, newUserMessage]
		setMessages(updatedMessages)

		setInput("")
		if (textareaRef.current) textareaRef.current.style.height = "auto"
		setThinking(true)
		abortControllerRef.current = new AbortController()

		const apiMessages = updatedMessages.map(({ role, content, id }) => ({
			role,
			content,
			id
		}))

		try {
			const response = await fetch("/api/chat/message", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					messages: apiMessages,
					chatId: activeChatId
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

						if (parsed.type === "chat_session") {
							const { chatId: newChatId } = parsed
							// FIX: Update URL without navigation to prevent aborting the stream
							window.history.replaceState(
								null,
								"",
								`/chat/${newChatId}`
							)
							setActiveChatId(newChatId)

							// Optimistically update the list
							setChatList((prev) => {
								const existing = prev.find(
									(c) => c.chat_id === newChatId
								)
								if (!existing) {
									return [
										{
											chat_id: newChatId,
											title:
												input.substring(0, 40) + "...",
											updated_at: new Date().toISOString()
										},
										...prev
									]
								}
								return prev
							})
							continue
						} else if (parsed.type === "error") {
							toast.error(`An error occurred: ${parsed.message}`)
							continue
						}

						if (parsed.type === "assistantStream") {
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
													content: msg.content + token
												}
											: msg
									)
								} else {
									return [
										...prev,
										{
											id: assistantMessageId,
											role: "assistant",
											content: token,
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
			if (error.name !== "AbortError") {
				toast.error(`Error: ${error.message}`)
			}
		} finally {
			setThinking(false)
			abortControllerRef.current = null
		}
	}

	const handleStopStreaming = () => {
		if (abortControllerRef.current) {
			abortControllerRef.current.abort()
			toast.info("Message generation stopped.")
		}
	}

	const handleNewChat = () => {
		setActiveChatId(null)
		setMessages([])
		router.push("/chat")
	}

	const handleDeleteChat = async (chatIdToDelete) => {
		if (
			!window.confirm(
				"Are you sure you want to delete this conversation?"
			)
		)
			return

		const originalList = [...chatList]
		setChatList((prev) => prev.filter((c) => c.chat_id !== chatIdToDelete))

		if (activeChatId === chatIdToDelete) {
			router.push("/chat")
		}

		try {
			const res = await fetch(`/api/chat/${chatIdToDelete}`, {
				method: "DELETE"
			})
			if (!res.ok) throw new Error("Failed to delete chat")
			toast.success("Chat deleted.")
		} catch (error) {
			toast.error(error.message)
			setChatList(originalList) // Revert on error
		}
	}

	useEffect(() => {
		if (chatEndRef.current)
			chatEndRef.current.scrollIntoView({ behavior: "smooth" })
	}, [messages, thinking])

	const getGreeting = () => {
		const hour = new Date().getHours()
		if (hour < 12) return "Good Morning"
		if (hour < 18) return "Good Afternoon"
		return "Good Evening"
	}

	return (
		<div className="flex-1 flex bg-black text-white overflow-hidden">
			<Tooltip id="home-tooltip" place="right" style={{ zIndex: 9999 }} />
			<ChatHistorySidebar
				chatList={chatList}
				activeChatId={activeChatId}
				onSelectChat={(id) => router.push(`/chat/${id}`)}
				onNewChat={handleNewChat}
				onDeleteChat={handleDeleteChat}
				isLoading={isLoadingHistory}
				onClose={() => setIsHistoryOpen(false)}
				isSidebarOpen={isHistoryOpen}
			/>
			<div className="flex flex-col flex-1 relative bg-black pb-16 md:pb-0">
				<div className="absolute top-6 left-6 z-20 flex items-center gap-1">
					<button
						onClick={() => setIsHistoryOpen(!isHistoryOpen)}
						className="p-2 bg-transparent text-neutral-400 hover:text-white hover:bg-neutral-800/50 rounded-lg transition-colors"
						data-tooltip-id="home-tooltip"
						data-tooltip-content={
							isHistoryOpen ? "Hide History" : "Show History"
						}
					>
						{isHistoryOpen ? (
							<IconLayoutSidebarLeftCollapse size={20} />
						) : (
							<IconLayoutSidebarLeftExpand size={20} />
						)}
					</button>
					<button
						onClick={handleNewChat}
						className="p-2 bg-transparent text-neutral-400 hover:text-white hover:bg-neutral-800/50 rounded-lg transition-colors"
						data-tooltip-id="home-tooltip"
						data-tooltip-content="New Chat"
					>
						<IconPlus size={20} />
					</button>
				</div>
				{!activeChatId && (
					<div className="absolute inset-0 h-full w-full bg-gradient-to-br from-neutral-900 to-black bg-[linear-gradient(110deg,#09090b,45%,#1e293b,55%,#09090b)] bg-[length:200%_100%] animate-shimmer" />
				)}
				<main
					ref={scrollContainerRef}
					className="flex-1 overflow-y-auto p-6 flex flex-col custom-scrollbar z-10"
				>
					{messages.length === 0 &&
					!thinking &&
					!isLoadingMessages ? (
						<div className="flex-1 flex flex-col justify-center items-center p-6 text-center">
							<div>
								<h1 className="text-4xl sm:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-100 to-neutral-400 py-4">
									{getGreeting()}, {userDetails?.given_name}
								</h1>
								<p className="mt-2 text-lg text-neutral-400">
									How can I help you today?
								</p>
							</div>
							<div className="w-full max-w-4xl mx-auto mt-12">
								<div className="w-full max-w-4xl mx-auto">
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
												onFocus={() =>
													setIsFocused(true)
												}
												onBlur={() =>
													setIsFocused(false)
												}
												onKeyDown={(e) => {
													if (
														e.key === "Enter" &&
														!e.shiftKey
													) {
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
														onClick={
															handleStopStreaming
														}
														className="p-2.5 rounded-full text-white bg-red-600 hover:bg-red-500 transition-colors"
														data-tooltip-id="home-tooltip"
														data-tooltip-content="Stop Generation"
													>
														<IconPlayerStopFilled
															size={18}
														/>
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
									<div className="mt-12">
										<DomainSelector
											domains={Object.keys(
												useCasesByDomain
											)}
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
						</div>
					) : (
						<div className="w-full max-w-4xl mx-auto flex flex-col gap-4 flex-1">
							{isLoadingMessages ? (
								<div className="flex-1 flex justify-center items-center">
									<IconLoader className="animate-spin text-neutral-500" />
								</div>
							) : (
								messages.map((msg, i) => (
									<div
										key={msg.id || i}
										className={`flex w-full ${
											msg.role === "user"
												? "justify-end"
												: "justify-start"
										}`}
									>
										<ChatBubble
											message={msg.content}
											isUser={msg.role === "user"}
											memoryUsed={msg.memoryUsed}
											agentsUsed={msg.agentsUsed}
											internetUsed={msg.internetUsed}
										/>
									</div>
								))
							)}
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

				{messages.length > 0 && !isLoadingMessages && (
					<div className="px-4 pt-2 pb-4 sm:px-6 sm:pb-6 bg-black border-t border-neutral-800/50">
						<div className="w-full max-w-4xl mx-auto">
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
											if (
												e.key === "Enter" &&
												!e.shiftKey
											) {
												e.preventDefault()
												sendMessage()
											}
										}}
										placeholder="Ask me anything..."
										className="w-full p-4 pr-24 bg-transparent text-base text-white placeholder-neutral-500 resize-none focus:outline-none overflow-y-auto custom-scrollbar"
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
												<IconPlayerStopFilled
													size={18}
												/>
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
						</div>
					</div>
				)}
			</div>
		</div>
	)
}
