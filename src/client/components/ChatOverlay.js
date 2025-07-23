"use client"
import React, { useState, useEffect, useRef, useCallback } from "react"
import {
	IconSend,
	IconLoader,
	IconPlayerStopFilled,
	IconX,
	IconPlus,
	IconTrash,
	IconMessage,
	IconLayoutSidebarLeftCollapse,
	IconLayoutSidebarLeftExpand
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"
import { usePostHog } from "posthog-js/react"
import { motion, AnimatePresence } from "framer-motion"
import { formatDistanceToNow } from "date-fns"
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
			animate={{ width: isSidebarOpen ? 260 : 60 }}
			transition={{ type: "spring", stiffness: 300, damping: 30 }}
			className="bg-neutral-900/50 flex flex-col h-full border-r border-[var(--color-primary-surface)] flex-shrink-0"
		>
			<div className="flex items-center justify-between p-3 border-b border-[var(--color-primary-surface)]">
				{isSidebarOpen && (
					<h3 className="font-semibold text-white">Conversations</h3>
				)}
				<button
					onClick={toggleSidebar}
					className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded-lg"
				>
					{isSidebarOpen ? (
						<IconLayoutSidebarLeftCollapse size={18} />
					) : (
						<IconLayoutSidebarLeftExpand size={18} />
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
									"w-full text-left p-2.5 rounded-lg transition-colors text-sm flex items-center gap-3",
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
			<div className="p-2 border-t border-[var(--color-primary-surface)]">
				<button
					onClick={onNewChat}
					className="w-full flex items-center justify-center gap-2 p-3 rounded-lg text-neutral-200 hover:bg-neutral-700/50 hover:text-white transition-colors"
				>
					<IconPlus size={18} />
					{isSidebarOpen && (
						<span className="font-medium text-sm">New Chat</span>
					)}
				</button>
			</div>
		</motion.div>
	)
}

const ChatOverlay = ({ onClose }) => {
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
	const abortControllerRef = useRef(null) // To abort fetch requests
	const posthog = usePostHog()
	const scrollContainerRef = useRef(null) // For scrolling

	useEffect(() => {
		const fetchHistory = async () => {
			setIsLoadingHistory(true)
			try {
				const res = await fetch("/api/chat/history")
				if (!res.ok) throw new Error("Failed to fetch chat history")
				const data = await res.json()
				setChatList(data.chats || [])
				if (data.chats && data.chats.length > 0) {
					setActiveChatId(data.chats[0].chat_id)
				}
			} catch (error) {
				toast.error(error.message)
			} finally {
				setIsLoadingHistory(false)
			}
		}
		fetchHistory()

		return () => {
			if (abortControllerRef.current) {
				abortControllerRef.current.abort()
			}
		}
	}, [])

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
		if (input.trim() === "") return
		posthog?.capture("chat_message_sent", {
			message_length: input.length
		})
		const newUserMessage = {
			role: "user",
			content: input,
			id: Date.now()
		}

		// Add new message and create history for API call
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
					if (line.trim() === "") continue // Skip empty lines
					try {
						const parsed = JSON.parse(line)
						if (parsed.type === "chat_session") {
							const { chatId: newChatId, tempTitle } = parsed
							setActiveChatId(newChatId)
							setChatList((prev) => [
								{
									chat_id: newChatId,
									title: tempTitle,
									updated_at: new Date().toISOString()
								},
								...prev
							])
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
			if (error.name !== "AbortError")
				toast.error(`Error: ${error.message}`)
		} finally {
			setThinking(false)
		}
	}

	const handleStopStreaming = () => {
		if (abortControllerRef.current) {
			abortControllerRef.current.abort()
		}
	}

	const handleNewChat = () => {
		setActiveChatId(null)
		setMessages([])
		setInput("")
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
		// Auto-scroll to bottom, using smooth behavior
		if (chatEndRef.current)
			chatEndRef.current.scrollIntoView({ behavior: "smooth" })
	}, [messages, thinking]) // Rerun whenever messages change or thinking state changes
	const handleBackdropClick = (e) => {
		if (e.target === e.currentTarget) {
			onClose()
		}
	}

	return (
		<div
			onClick={handleBackdropClick}
			className="fixed inset-0 bg-black/50 backdrop-blur-md z-50 flex items-center justify-center p-4"
		>
			<Tooltip
				id="chat-overlay-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>
			<motion.div
				initial={{ opacity: 0, y: 50, scale: 0.9 }}
				animate={{ opacity: 1, y: 0, scale: 1 }}
				exit={{ opacity: 0, y: 50, scale: 0.9 }}
				transition={{ duration: 0.3, ease: "easeInOut" }}
				className="bg-[var(--color-primary-background)] border border-[var(--color-primary-surface-elevated)] rounded-2xl w-full max-w-5xl h-[90vh] flex shadow-2xl overflow-hidden"
			>
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

				<div className="flex flex-col flex-1">
					<header className="flex justify-between items-center p-4 border-b border-[var(--color-primary-surface)] flex-shrink-0">
						<h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
							Chat with Sentient
						</h2>
						<button
							onClick={onClose}
							className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
						>
							<IconX />
						</button>
					</header>

					<div
						ref={scrollContainerRef}
						className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 custom-scrollbar"
					>
						{messages.length === 0 && !thinking ? (
							<div className="flex-1 flex flex-col justify-center items-center text-gray-400">
								<p className="text-3xl text-[var(--color-text-primary)] mb-4 font-Inter text-center">
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
										memoryUsed={msg.memoryUsed}
										agentsUsed={msg.agentsUsed}
										internetUsed={msg.internetUsed}
									/>
								</div>
							))
						)}
						<AnimatePresence>
							{thinking && (
								<div className="flex justify-start w-full mt-2">
									<motion.div
										initial={{ opacity: 0, y: 10 }}
										animate={{ opacity: 1, y: 0 }}
										exit={{ opacity: 0 }}
										className="flex items-center gap-2 p-3 bg-gray-700 rounded-lg"
									>
										<div className="bg-gray-400 rounded-full h-2 w-2 animate-pulse delay-75"></div>
										<div className="bg-gray-400 rounded-full h-2 w-2 animate-pulse delay-150"></div>
										<div className="bg-gray-400 rounded-full h-2 w-2 animate-pulse delay-300"></div>
									</motion.div>
								</div>
							)}
						</AnimatePresence>
						<div ref={chatEndRef} />{" "}
						{/* This empty div is the target for scrolling */}
					</div>

					<div className="p-4 border-t border-[var(--color-primary-surface)]">
						<div className="relative w-full flex flex-row gap-4 items-end px-4 py-2 bg-[var(--color-primary-background)] border-[1px] border-[var(--color-primary-surface-elevated)] rounded-lg">
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
								className="flex-grow p-2 pr-28 rounded-lg bg-transparent text-base text-[var(--color-text-primary)] focus:outline-none focus:ring-0 resize-none no-scrollbar overflow-y-auto"
								placeholder="Type your message..."
								style={{ maxHeight: "150px" }}
								rows={1}
							/>
							<div className="absolute right-4 bottom-3 flex flex-row items-center gap-2">
								{thinking ? (
									<button
										onClick={handleStopStreaming}
										className="p-2 hover-button scale-100 hover:scale-110 cursor-pointer rounded-full text-white bg-[var(--color-accent-red)] hover:bg-[var(--color-accent-red-hover)]"
										data-tooltip-id="chat-overlay-tooltip"
										data-tooltip-content="Stop Generation"
									>
										<IconPlayerStopFilled className="w-4 h-4 text-white" />
									</button>
								) : (
									<button
										onClick={sendMessage}
										disabled={input.trim() === ""}
										className="p-2 hover-button scale-100 hover:scale-110 cursor-pointer rounded-full text-white disabled:opacity-50 disabled:cursor-not-allowed bg-[var(--color-accent-blue)]"
										data-tooltip-id="chat-overlay-tooltip"
										data-tooltip-content="Send Message"
									>
										<IconSend className="w-4 h-4 text-white" />
									</button>
								)}
							</div>
						</div>
					</div>
				</div>
			</motion.div>
		</div>
	)
}

export default ChatOverlay
