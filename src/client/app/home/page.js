"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import {
	IconSend,
	IconLoader,
	IconPlayerStopFilled,
	IconPlus,
	IconTrash,
	IconMessage,
	IconLayoutSidebarLeftCollapse,
	IconLayoutSidebarLeftExpand
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"
import { motion, AnimatePresence } from "framer-motion"
import ChatBubble from "@components/ChatBubble"

const ChatHistorySidebar = ({
	chatList,
	activeChatId,
	onSelectChat,
	onNewChat,
	onDeleteChat,
	isLoading,
	isSidebarOpen,
	toggleSidebar
}) => {
	return (
		<motion.div
			initial={false}
			animate={{ width: isSidebarOpen ? 280 : 70 }}
			transition={{ type: "spring", stiffness: 300, damping: 30 }}
			className="bg-neutral-900/50 flex flex-col h-full border-r border-[var(--color-primary-surface)] flex-shrink-0"
		>
			<div className="flex items-center justify-between p-4 border-b border-[var(--color-primary-surface)]">
				{isSidebarOpen && (
					<h3 className="font-semibold text-white text-lg">
						Conversations
					</h3>
				)}
				<button
					onClick={toggleSidebar}
					className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded-lg"
				>
					{isSidebarOpen ? (
						<IconLayoutSidebarLeftCollapse size={20} />
					) : (
						<IconLayoutSidebarLeftExpand size={20} />
					)}
				</button>
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
								{isSidebarOpen && (
									<span className="truncate flex-1">
										{chat.title}
									</span>
								)}
							</button>
							{isSidebarOpen && activeChatId === chat.chat_id && (
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
			<div className="p-3 border-t border-[var(--color-primary-surface)]">
				<button
					onClick={onNewChat}
					className="w-full flex items-center justify-center gap-2 p-3 rounded-lg text-neutral-200 hover:bg-neutral-700/50 hover:text-white transition-colors"
				>
					<IconPlus size={20} />
					{isSidebarOpen && (
						<span className="font-medium">New Chat</span>
					)}
				</button>
			</div>
		</motion.div>
	)
}

const HomePage = () => {
	const [isSidebarOpen, setIsSidebarOpen] = useState(true)
	const [chatList, setChatList] = useState([])
	const [activeChatId, setActiveChatId] = useState(null)
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

	const fetchHistory = useCallback(async () => {
		setIsLoadingHistory(true)
		try {
			const res = await fetch("/api/chat/history")
			if (!res.ok) throw new Error("Failed to fetch chat history")
			const data = await res.json()
			setChatList(data.chats || [])
			if (data.chats && data.chats.length > 0 && !activeChatId) {
				setActiveChatId(data.chats[0].chat_id)
			}
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoadingHistory(false)
		}
	}, [activeChatId])

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

	const sendMessage = async () => {
		// This function would be identical to the one in ChatOverlay.js
		// For brevity, I'll include a placeholder. The full implementation
		// from ChatOverlay.js should be used here.
		if (input.trim() === "") return

		const userMessage = { id: Date.now(), role: "user", content: input }
		setMessages((prev) => [...prev, userMessage])
		setInput("")
		if (textareaRef.current) {
			textareaRef.current.style.height = "auto"
		}

		setThinking(true)
		abortControllerRef.current = new AbortController()
		const signal = abortControllerRef.current.signal

		try {
			// Simulate AI response
			await new Promise((resolve) => setTimeout(resolve, 1500))

			const aiResponseContent = `Hello ${
				userDetails?.given_name || "there"
			}! I received your message: "${userMessage.content}". This is a simulated response.`
			const aiMessage = {
				id: Date.now() + 1,
				role: "assistant",
				content: aiResponseContent
			}
			setMessages((prev) => [...prev, aiMessage])

			// If it's a new chat, simulate updating chat history
			if (!activeChatId) {
				const newChatId = "chat_" + Date.now()
				const newChatTitle =
					userMessage.content.substring(0, 30) +
					(userMessage.content.length > 30 ? "..." : "")
				setChatList((prev) => [
					{ chat_id: newChatId, title: newChatTitle },
					...prev
				])
				setActiveChatId(newChatId)
			}
		} catch (error) {
			if (signal.aborted) {
				toast.info("Message generation stopped.")
			} else {
				toast.error(error.message)
			}
		} finally {
			setThinking(false)
			abortControllerRef.current = null
		}
	}

	const handleNewChat = () => {
		setActiveChatId(null)
		setMessages([])
		setInput("")
		if (textareaRef.current) {
			textareaRef.current.style.height = "auto"
		}
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
			handleNewChat()
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
		<div className="flex h-screen w-full bg-black text-white overflow-hidden md:pl-20">
			<Tooltip id="home-tooltip" place="right" style={{ zIndex: 9999 }} />
			<ChatHistorySidebar
				chatList={chatList}
				activeChatId={activeChatId}
				onSelectChat={setActiveChatId}
				onNewChat={handleNewChat}
				onDeleteChat={handleDeleteChat}
				isLoading={isLoadingHistory}
				isSidebarOpen={isSidebarOpen}
				toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
			/>
			<div className="flex flex-col flex-1 relative bg-black">
				<div className="absolute inset-0 h-full w-full bg-gradient-to-br from-neutral-900 to-black bg-[linear-gradient(110deg,#09090b,45%,#1e293b,55%,#09090b)] bg-[length:200%_100%] animate-shimmer" />

				<main
					ref={scrollContainerRef}
					className="flex-1 overflow-y-auto p-6 flex flex-col gap-4 custom-scrollbar z-10"
				>
					{messages.length === 0 &&
					!thinking &&
					!isLoadingMessages ? (
						<div className="flex-1 flex flex-col justify-center items-center text-center">
							<h1 className="text-4xl sm:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-100 to-neutral-400 py-4">
								{getGreeting()}, {userDetails?.given_name}
							</h1>
							<p className="mt-2 text-lg text-neutral-400">
								How can I help you today?
							</p>
						</div>
					) : isLoadingMessages ? (
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
				</main>

				<footer className="p-4 sm:p-6 z-10">
					<div className="w-full max-w-4xl mx-auto p-0.5 rounded-2xl bg-gradient-to-tr from-blue-500 to-cyan-500 shadow-2xl shadow-black/40">
						<div className="relative bg-neutral-900 rounded-[15px] flex items-end">
							<textarea
								ref={textareaRef}
								value={input}
								onChange={handleInputChange}
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
										// onClick={handleStopStreaming}
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
				</footer>
			</div>
		</div>
	)
}

export default HomePage
