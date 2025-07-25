"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import toast from "react-hot-toast"
import { motion, AnimatePresence } from "framer-motion"
import { IconLoader, IconSend, IconPlayerStopFilled } from "@tabler/icons-react"
import ChatBubble from "@components/ChatBubble"
import { useUser } from "@auth0/nextjs-auth0"

const ProjectChatView = ({
	project,
	activeChatId,
	onChatCreated,
	onNewMessage
}) => {
	const { user: currentUser } = useUser()
	const [messages, setMessages] = useState([])
	const [input, setInput] = useState("")
	const [isLoading, setIsLoading] = useState(false)
	const [isStreaming, setIsStreaming] = useState(false)
	const textareaRef = useRef(null)
	const chatEndRef = useRef(null)
	const abortControllerRef = useRef(null)
	const isCreatingChatRef = useRef(false)

	const fetchMessages = useCallback(async () => {
		if (!activeChatId) {
			setMessages([])
			return
		}
		setIsLoading(true)
		// Do not fetch if we are in the middle of creating this chat
		if (isCreatingChatRef.current) {
			setIsLoading(false)
			return
		}
		try {
			const res = await fetch(`/api/chat/history/${activeChatId}`)
			if (!res.ok) throw new Error("Failed to fetch messages")
			const data = await res.json()
			setMessages(data.messages || [])
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [activeChatId])

	useEffect(() => {
		fetchMessages()
	}, [fetchMessages])

	useEffect(() => {
		chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
	}, [messages, isStreaming])

	const handleInputChange = (e) => {
		const value = e.target.value
		setInput(value)
		if (textareaRef.current) {
			textareaRef.current.style.height = "auto"
			textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
		}
	}

	const sendMessage = async () => {
		if (input.trim() === "" || isStreaming) return

		const newUserMessage = {
			role: "user",
			content: input,
			sender_id: currentUser?.sub,
			id: Date.now().toString()
		}

		const updatedMessages = [...messages, newUserMessage]
		setMessages(updatedMessages)
		setInput("")
		if (textareaRef.current) textareaRef.current.style.height = "auto"
		setIsStreaming(true)
		abortControllerRef.current = new AbortController()

		if (!activeChatId) {
			isCreatingChatRef.current = true
		}

		try {
			const response = await fetch("/api/chat/message", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					messages: updatedMessages.map(
						({ role, content, sender_id }) => ({
							role,
							content,
							sender_id
						})
					),
					chatId: activeChatId,
					projectId: project.project_id
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
					if (line.trim() === "") return

					try {
						const parsed = JSON.parse(line)
						if (
							parsed.type === "chat_session" &&
							!activeChatId
						) {
							onChatCreated(parsed)
						} else if (parsed.type === "error") {
							toast.error(
								`An error occurred: ${parsed.message}`
							)
							continue
						} else if (parsed.type === "assistantStream") {
							const token = parsed.token || ""
							assistantMessageId = parsed.messageId

							setMessages((prev) => {
								const existingMsgIndex = prev.findIndex(
									(msg) => msg.id === assistantMessageId
								)
								if (existingMsgIndex !== -1) {
									return prev.map(
										(msg, index) =>
											index === existingMsgIndex
												? {
														...msg,
														content:
															msg.content + token
													}
												: msg
									)
								} else {
									return [
										...prev,
										{
											id: assistantMessageId,
											role: "assistant",
											content: token
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
			setIsStreaming(false)
			abortControllerRef.current = null
			isCreatingChatRef.current = false
			// After stream ends, tell parent a new message was added to trigger a project data refresh
			onNewMessage()
		}
	}

	const getSenderInfo = (senderId) => {
		if (!senderId)
			return { name: "User", picture: "/images/half-logo-dark.svg" }
		const member = project.members.find((m) => m.user_id === senderId)
		// This needs a way to fetch profile pics. For now, we'll use a placeholder.
		// A robust solution would involve an API endpoint to get user profiles by ID.
		return {
			name: member
				? `Member (${member.user_id.slice(0, 10)}...)`
				: "Unknown User",
			picture: `https://i.pravatar.cc/150?u=${senderId}`
		}
	}

	return (
		<div className="flex flex-col h-full">
			<div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
				{isLoading ? (
					<div className="flex-1 flex justify-center items-center">
						<IconLoader className="animate-spin text-neutral-500" />
					</div>
				) : (
					messages.map((msg, i) => {
						const senderInfo =
							msg.role === "user"
								? getSenderInfo(msg.sender_id)
								: {}
						return (
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
									isProjectChat={true}
									senderName={senderInfo.name}
									senderPicture={senderInfo.picture}
								/>
							</div>
						)
					})
				)}
				<AnimatePresence>
					{isStreaming && (
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
			<div className="p-4 border-t border-neutral-800">
				<div className="relative bg-neutral-900 rounded-lg flex items-end">
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
						placeholder="Send a message to the project..."
						className="w-full p-3 pr-20 bg-transparent text-white placeholder-neutral-500 resize-none focus:outline-none overflow-y-auto custom-scrollbar"
						rows={1}
						style={{ maxHeight: "150px" }}
					/>
					<div className="absolute right-2 bottom-2 flex items-center gap-2">
						{isStreaming ? (
							<button
								onClick={() =>
									abortControllerRef.current?.abort()
								}
								className="p-2.5 rounded-full text-white bg-red-600 hover:bg-red-500 transition-colors"
							>
								<IconPlayerStopFilled size={16} />
							</button>
						) : (
							<button
								onClick={sendMessage}
								disabled={!input.trim()}
								className="p-2.5 bg-blue-600 rounded-full text-white disabled:opacity-50 hover:bg-blue-500 transition-colors"
							>
								<IconSend size={16} />
							</button>
						)}
					</div>
				</div>
			</div>
		</div>
	)
}

export default ProjectChatView
