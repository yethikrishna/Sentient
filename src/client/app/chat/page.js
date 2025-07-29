"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { usePostHog } from "posthog-js/react"
import {
	IconSend,
	IconLoader,
	IconPlayerStopFilled,
	IconBrain,
	IconWorldSearch,
	IconUsers,
	IconMapPin
} from "@tabler/icons-react"
import {
	IconBrandGoogle,
	IconBrandYoutube,
	IconBrandInstagram
} from "@tabler/icons-react"

import IconGoogleMail from "@components/icons/IconGoogleMail"
import { Textarea } from "@components/ui/textarea"
import { Button } from "@components/ui/button"
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle
} from "@components/ui/card"
import toast from "react-hot-toast"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"
import { motion, AnimatePresence } from "framer-motion"
import ChatBubble from "@components/ChatBubble"

const toolIcons = {
	gmail: IconGoogleMail,
	google: IconBrandGoogle,
	youtube: IconBrandYoutube,
	instagram: IconBrandInstagram,
	brave_search: IconBrain,
	google_search: IconWorldSearch,
	tavily_search: IconUsers,
	maps: IconMapPin
}

const ChatInput = React.forwardRef(
	(
		{ input, handleInputChange, handleKeyDown, handleSubmit, thinking },
		ref
	) => {
		const isInputEmpty = input.trim() === ""

		return (
			<div className="relative flex items-center w-full">
				<Textarea
					ref={ref}
					value={input}
					onChange={handleInputChange}
					onKeyDown={handleKeyDown}
					placeholder="Message AI..."
					className="min-h-12 w-full resize-none rounded-2xl border-none bg-neutral-800 p-3 pr-12 text-sm text-neutral-100 placeholder:text-neutral-400 focus:outline-none focus:ring-1 focus:ring-[var(--color-primary-surface)] custom-scrollbar"
					rows={1}
					tabIndex={0}
					disabled={thinking}
				/>
				<Button
					type="submit"
					size="icon"
					className="absolute right-3 top-1/2 -translate-y-1/2 bg-[var(--color-accent-blue)] text-white hover:bg-[var(--color-accent-blue-dark)] rounded-full transition-colors duration-200"
					onClick={handleSubmit}
					disabled={isInputEmpty || thinking}
				>
					{thinking ? (
						<IconPlayerStopFilled size={20} />
					) : (
						<IconSend size={20} />
					)}
				</Button>
			</div>
		)
	}
)
ChatInput.displayName = "ChatInput"

export default function ChatPage() {
	const [activeDomain, setActiveDomain] = useState("Featured")
	const [messages, setMessages] = useState([])
	const [input, setInput] = useState("")
	const [isLoading, setIsLoading] = useState(true)
	const [thinking, setThinking] = useState(false)
	const textareaRef = useRef(null)
	const chatEndRef = useRef(null)
	const abortControllerRef = useRef(null)
	const scrollContainerRef = useRef(null)
	const scrollPositionRef = useRef(null) // For preserving scroll on new messages

	// State for infinite scroll
	const [isLoadingOlder, setIsLoadingOlder] = useState(false)
	const [hasMoreMessages, setHasMoreMessages] = useState(true)
	const [userDetails, setUserDetails] = useState(null)
	const posthog = usePostHog()
	const [isFocused, setIsFocused] = useState(false)

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
			}
		} catch (error) {
			console.error("Failed to fetch user details:", error)
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
				// Store the current scroll height before adding new messages
				const oldScrollHeight = scrollContainer.scrollHeight

				setMessages((prev) => [...data.messages, ...prev])
				setHasMoreMessages(data.messages.length === 50)

				// After state update, restore scroll position relative to the bottom
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

	// Effect for handling infinite scroll
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
		adjustTextareaHeight()
	}

	const adjustTextareaHeight = () => {
		const textarea = textareaRef.current
		if (textarea) {
			textarea.style.height = "auto"
			textarea.style.height = `${textarea.scrollHeight}px`
		}
	}

	const handleKeyDown = (e) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault()
			handleSubmit(e)
		}
	}

	const handleSubmit = async (e) => {
		e.preventDefault()
		if (thinking) {
			abortControllerRef.current?.abort()
			setThinking(false)
			return
		}

		const trimmedInput = input.trim()
		if (!trimmedInput) return

		// Add user message to state
		const newUserMessage = {
			id: `user-${Date.now()}`,
			role: "user",
			content: trimmedInput,
			timestamp: new Date().toISOString()
		}
		setMessages((prev) => [...prev, newUserMessage])
		setInput("")
		adjustTextareaHeight()
		setThinking(true)

		abortControllerRef.current = new AbortController()

		try {
			const apiMessages = [...messages, newUserMessage].map((msg) => ({
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
			let receivedContent = ""
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
							toast.error(`An error occurred: ${parsed.message}`)
							continue
						}

						setMessages((prev) =>
							prev.map((msg) => {
								if (msg.id === assistantMessageId) {
									return {
										...msg,
										content: msg.content + (parsed.token || ""),
										tools: parsed.tools || msg.tools
									}
								}
								return msg
							})
						)
					} catch (parseError) {
						console.warn("Failed to parse JSON:", line, parseError)
						// Append as raw text if not valid JSON
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

	useEffect(() => {
		if (chatEndRef.current)
			chatEndRef.current.scrollIntoView({ behavior: "smooth" })
	}, [messages, thinking])

	useEffect(() => {
		if (textareaRef.current) {
			textareaRef.current.focus()
		}
	}, [isFocused])

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
					{messages.length === 0 && !thinking && !isLoading ? (
						<div className="flex-1 flex flex-col justify-center items-center p-6 text-center">
							<div>
								<h1 className="text-4xl sm:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-100 to-neutral-400 py-4">
									Hi, I'm Synapse.
								</h1>
								<p className="text-lg sm:text-xl text-neutral-300 mb-8">
									Your AI assistant built with{" "}
									<span className="text-[var(--color-accent-blue)] font-medium">
										Next.js
									</span>{" "}
									and{" "}
									<span className="text-[var(--color-accent-blue)] font-medium">
										OpenAI
									</span>
									.
								</p>
							</div>
							<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-4xl mt-8">
								<Card className="bg-neutral-900/50 border border-neutral-800 text-neutral-200 hover:border-[var(--color-accent-blue)] transition-colors cursor-pointer">
									<CardHeader>
										<CardTitle className="text-lg flex items-center gap-2">
											<IconBrain size={20} /> General AI
										</CardTitle>
										<CardDescription className="text-neutral-400 text-sm">
											Ask me anything, I'm here to help.
										</CardDescription>
									</CardHeader>
									<CardContent className="text-sm text-neutral-300">
										"Explain quantum physics in simple
										terms."
									</CardContent>
								</Card>
								<Card className="bg-neutral-900/50 border border-neutral-800 text-neutral-200 hover:border-[var(--color-accent-blue)] transition-colors cursor-pointer">
									<CardHeader>
										<CardTitle className="text-lg flex items-center gap-2">
											<IconWorldSearch size={20} /> Search
										</CardTitle>
										<CardDescription className="text-neutral-400 text-sm">
											I can search the web for you.
										</CardDescription>
									</CardHeader>
									<CardContent className="text-sm text-neutral-300">
										"What's the weather like in New York
										City today?"
									</CardContent>
								</Card>
								<Card className="bg-neutral-900/50 border border-neutral-800 text-neutral-200 hover:border-[var(--color-accent-blue)] transition-colors cursor-pointer">
									<CardHeader>
										<CardTitle className="text-lg flex items-center gap-2">
											<IconUsers size={20} /> Personal
										</CardTitle>
										<CardDescription className="text-neutral-400 text-sm">
											I can help with daily tasks once
											connected.
										</CardDescription>
									</CardHeader>
									<CardContent className="text-sm text-neutral-300">
										"Summarize my latest emails."
									</CardContent>
								</Card>
							</div>
						</div>
					) : (
						<div className="w-full max-w-4xl mx-auto flex flex-col gap-4 flex-1">
							{isLoading ? (
								<div className="flex-1 flex justify-center items-center">
									<IconLoader className="animate-spin text-neutral-500" />
								</div>
							) : (
								<>
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
								</>
							)}
							<AnimatePresence>
								{thinking && (
									<motion.div
										initial={{ opacity: 0, y: 20 }}
										animate={{ opacity: 1, y: 0 }}
										exit={{ opacity: 0, y: 20 }}
										transition={{ duration: 0.2 }}
										className="flex justify-start"
									>
										<div className="p-4 rounded-lg bg-transparent text-base text-white self-start mb-2 relative">
											<IconLoader className="animate-spin text-neutral-400" />
										</div>
									</motion.div>
								)}
							</AnimatePresence>
							<div ref={chatEndRef} />
						</div>
					)}
				</main>

				{messages.length > 0 && !isLoading && (
					<div className="px-4 pt-2 pb-4 sm:px-6 sm:pb-6 bg-black border-t border-neutral-800/50">
						<div className="w-full max-w-4xl mx-auto">
							<ChatInput
								ref={textareaRef}
								input={input}
								handleInputChange={handleInputChange}
								handleKeyDown={handleKeyDown}
								handleSubmit={handleSubmit}
								thinking={thinking}
							/>
						</div>
					</div>
				)}
				{messages.length === 0 && !isLoading && (
					<div className="absolute bottom-0 left-0 right-0 p-4 sm:p-6 bg-black">
						<div className="w-full max-w-4xl mx-auto">
							<ChatInput
								ref={textareaRef}
								input={input}
								handleInputChange={handleInputChange}
								handleKeyDown={handleKeyDown}
								handleSubmit={handleSubmit}
								thinking={thinking}
							/>
						</div>
					</div>
				)}
			</div>
		</div>
	)
}
