"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { useRouter, usePathname, useParams } from "next/navigation"
import { IconSend, IconPlus, IconLoader } from "@tabler/icons-react"
import ChatBubble from "@components/ChatBubble"
import toast from "react-hot-toast"

export default function HomePage() {
	const router = useRouter()
	const pathname = usePathname()
	const params = useParams()

	const [chatId, setChatId] = useState(null)
	const [messages, setMessages] = useState([])
	const [input, setInput] = useState("")
	const [isLoading, setIsLoading] = useState(false)
	const [isStreaming, setIsStreaming] = useState(false)
	const messagesEndRef = useRef(null)

	// Existing useEffect for params and pathname
	useEffect(() => {
		const urlChatId =
			params.chatId ||
			(Array.isArray(params.slug) ? params.slug[0] : null)
		if (!urlChatId && pathname === "/chat") {
			setMessages([])
			setChatId(null)
			return
		}
		setChatId(urlChatId)
	}, [params, pathname])

	// Existing useEffect for fetching history
	useEffect(() => {
		const fetchHistory = async () => {
			if (!chatId) {
				setMessages([])
				return
			}
			setIsLoading(true)
			try {
				const response = await fetch(`/api/chat/${chatId}/history`)
				if (!response.ok) {
					throw new Error(`HTTP error! status: ${response.status}`)
				}
				const data = await response.json()
				setMessages(data.messages)
			} catch (error) {
				console.error("Failed to fetch chat history:", error)
				toast.error("Failed to load chat history.")
				setMessages([])
			} finally {
				setIsLoading(false)
			}
		}
		fetchHistory()
	}, [chatId])

	// New useEffect for route change
	useEffect(() => {
		const handleRouteChange = (url) => {
			if (url === "/chat") {
				setMessages([])
				setChatId(null)
			}
		}

		router.events.on("routeChangeComplete", handleRouteChange)

		return () => {
			router.events.off("routeChangeComplete", handleRouteChange)
		}
	}, [router])

	const scrollToBottom = useCallback(() => {
		messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
	}, [])

	useEffect(scrollToBottom, [messages])

	const handleNewChat = () => {
		setMessages([]) // always clear messages
		setChatId(null) // clear current chatId so that new chat gets created
		router.push("/chat") // navigate to base chat page
	}

	const handleSend = async (e) => {
		e.preventDefault()
		if (!input.trim() || isStreaming) return

		const userMessage = { role: "user", content: input }
		setMessages((prev) => [...prev, userMessage])
		setInput("")
		setIsStreaming(true)
		setIsLoading(true)

		try {
			const response = await fetch("/api/chat", {
				method: "POST",
				headers: {
					"Content-Type": "application/json"
				},
				body: JSON.stringify({
					chat_id: chatId,
					message: input
				})
			})

			if (!response.ok || !response.body) {
				throw new Error(`HTTP error! status: ${response.status}`)
			}

			const assistantMessage = { role: "assistant", content: "" }
			setMessages((prev) => [...prev, assistantMessage])

			const reader = response.body.getReader()
			const decoder = new TextDecoder()
			let currentChatId = chatId

			while (true) {
				const { value, done } = await reader.read()
				if (done) break

				const chunk = decoder.decode(value, { stream: true })
				const lines = chunk
					.split("\n")
					.filter((line) => line.trim() !== "")

				for (const line of lines) {
					try {
						const json = JSON.parse(line)
						if (json.chat_id && !currentChatId) {
							const newChatId = json.chat_id
							// FIX: Update URL without a full page reload to preserve the stream
							window.history.replaceState(
								{},
								"",
								`/chat/${newChatId}`
							)
							setChatId(newChatId)
							currentChatId = newChatId // Update for subsequent chunks in this stream
						}
						if (json.token) {
							assistantMessage.content += json.token
							setMessages((prev) => {
								const newMessages = [...prev]
								newMessages[newMessages.length - 1] = {
									...assistantMessage
								}
								return newMessages
							})
						}
					} catch (error) {
						console.error(
							"Failed to parse JSON from stream:",
							error,
							"Line:",
							line
						)
					}
				}
			}
		} catch (error) {
			console.error("Streaming error:", error)
			toast.error("Failed to get response from AI.")
			setMessages((prev) => prev.slice(0, prev.length - 1)) // Remove the empty assistant message
		} finally {
			setIsStreaming(false)
			setIsLoading(false)
		}
	}

	return (
		<div className="flex-1 flex flex-col h-screen bg-neutral-900 text-white md:pl-20">
			<main className="flex-1 flex flex-col overflow-hidden">
				<header className="flex items-center justify-between p-4 border-b border-neutral-800">
					<h1 className="text-xl font-semibold">Chat</h1>
					<button
						onClick={handleNewChat}
						className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg bg-neutral-800 hover:bg-neutral-700"
					>
						<IconPlus size={16} /> New Chat
					</button>
				</header>
				<div className="flex-1 overflow-y-auto p-4 space-y-4">
					{messages.map((msg, i) => (
						<ChatBubble
							key={i}
							message={msg.content}
							isUser={msg.role === "user"}
						/>
					))}
					{isLoading && <IconLoader className="animate-spin" />}
					<div ref={messagesEndRef} />
				</div>
				<div className="p-4 border-t border-neutral-800">
					<form
						onSubmit={handleSend}
						className="flex items-center gap-3"
					>
						<input
							type="text"
							value={input}
							onChange={(e) => setInput(e.target.value)}
							placeholder="Ask Sentient anything..."
							className="flex-1 p-3 bg-neutral-800 rounded-lg focus:ring-2 focus:ring-blue-500"
							disabled={isStreaming}
						/>
						<button
							type="submit"
							className="p-3 bg-blue-600 rounded-lg"
							disabled={isStreaming || !input.trim()}
						>
							<IconSend size={20} />
						</button>
					</form>
				</div>
			</main>
		</div>
	)
}
