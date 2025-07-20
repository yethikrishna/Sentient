"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import {
	IconSparkles,
	IconLoader,
	IconBulb,
	IconUser,
	IconSend,
	IconPlus
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { motion, AnimatePresence } from "framer-motion"
import { Tooltip } from "react-tooltip"

const useCases = [
	{
		display:
			"Try asking me to 'summarize my unread emails from this morning'.",
		prompt: "summarize my unread emails from this morning"
	},
	{
		display:
			"Delegate tasks like 'draft a follow-up email to John about the Q3 report'.",
		prompt: "draft a follow-up email to John about the Q3 report"
	},
	{
		display:
			"Use me as a scratchpad: 'remember that the new server password is...'.",
		prompt: "remember that the new server password is..."
	},
	{
		display:
			"Schedule recurring tasks: 'remind me every Monday at 9 AM to prepare for the team meeting'.",
		prompt: "remind me every Monday at 9 AM to prepare for the team meeting"
	}
]

const RevolvingProTip = ({ onTipClick }) => {
	const [currentIndex, setCurrentIndex] = useState(0)

	useEffect(() => {
		const interval = setInterval(() => {
			setCurrentIndex((prevIndex) => (prevIndex + 1) % useCases.length)
		}, 5000) // Change tip every 5 seconds
		return () => clearInterval(interval)
	}, [])

	return (
		<div className="mt-16 md:mt-20 w-full max-w-3xl mx-auto flex flex-col items-center">
			<div className="flex items-center gap-2 text-neutral-400 w-full">
				<IconBulb className="text-yellow-400" />
				<div className="text-sm text-center relative h-10 overflow-hidden w-full">
					<AnimatePresence mode="wait">
						<motion.p
							key={currentIndex}
							initial={{ y: 20, opacity: 0 }}
							animate={{ y: 0, opacity: 1 }}
							exit={{ y: -20, opacity: 0 }}
							transition={{ ease: "easeInOut", duration: 0.5 }}
							className="absolute inset-0 cursor-pointer hover:text-white flex items-center justify-center"
							onClick={() =>
								onTipClick(useCases[currentIndex].prompt)
							}
						>
							{useCases[currentIndex].display}
						</motion.p>
					</AnimatePresence>
				</div>
			</div>
		</div>
	)
}

const CommandBar = ({ prompt, setPrompt, onSend, isSending }) => {
	const [assignee, setAssignee] = useState("ai") // 'ai' or 'user'
	const textareaRef = useRef(null)

	const handleSend = () => {
		if (prompt.trim()) {
			onSend(prompt, assignee)
		}
	}

	// Auto-resize textarea
	useEffect(() => {
		const textarea = textareaRef.current
		if (textarea) {
			textarea.style.height = "auto"
			const scrollHeight = textarea.scrollHeight
			textarea.style.height = `${scrollHeight}px`
		}
	}, [prompt])

	return (
		<div className="w-full max-w-3xl mx-auto p-0.5 rounded-2xl bg-gradient-to-tr from-blue-500 to-cyan-500 shadow-2xl shadow-black/40">
			<div className="relative bg-neutral-900 rounded-xl flex items-center">
				<textarea
					ref={textareaRef}
					value={prompt}
					onChange={(e) => setPrompt(e.target.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && !e.shiftKey) {
							e.preventDefault()
							handleSend()
						}
					}}
					placeholder="Assign a task to Sentient or yourself..."
					className="w-full p-4 sm:p-5 pr-28 sm:pr-36 bg-transparent text-base sm:text-lg text-white placeholder-neutral-500 resize-none focus:ring-0 focus:outline-none overflow-y-hidden max-h-48 custom-scrollbar"
					rows={1}
				/>
				<div className="absolute top-1/2 right-2 sm:right-3 -translate-y-1/2 flex items-center gap-1 sm:gap-2">
					<button
						onClick={() =>
							setAssignee(assignee === "ai" ? "user" : "ai")
						}
						className="p-2 rounded-full hover:bg-neutral-800"
						data-tooltip-id="home-tooltip"
						data-tooltip-content={`Assign to: ${assignee === "ai" ? "AI" : "Me"}`}
					>
						{assignee === "ai" ? (
							<IconSparkles className="text-[var(--color-accent-blue)]" />
						) : (
							<IconUser className="text-neutral-400" />
						)}
					</button>
					<button
						onClick={handleSend}
						disabled={isSending || !prompt.trim()}
						className="p-2.5 bg-gradient-to-tr from-blue-500 to-cyan-500 rounded-full text-white disabled:opacity-50 hover:from-blue-400 hover:to-cyan-400 transition-all shadow-md"
					>
						{isSending ? (
							<IconLoader className="animate-spin" />
						) : (
							<IconPlus size={20} />
						)}
					</button>
				</div>
			</div>
		</div>
	)
}

const HomePage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSending, setIsSending] = useState(false)
	const [prompt, setPrompt] = useState("")

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

	const handleSendCommand = async (prompt, assignee) => {
		setIsSending(true)
		try {
			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ prompt, assignee })
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to add task")
			}
			toast.success(data.message || "Task created successfully!")
			setPrompt("")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSending(false)
		}
	}

	const handleTipClick = (tipPrompt) => {
		setPrompt(tipPrompt)
	}

	useEffect(() => {
		fetchUserDetails()
	}, [fetchUserDetails])

	const getGreeting = () => {
		const hour = new Date().getHours()
		if (hour < 12) return "Good Morning"
		if (hour < 18) return "Good Afternoon"
		return "Good Evening"
	}

	return (
		<div className="font-Inter flex h-screen w-full flex-col items-center justify-center bg-black text-white overflow-hidden">
			<div className="absolute inset-0 h-full w-full bg-gradient-to-br from-neutral-900 to-black bg-[linear-gradient(110deg,#09090b,45%,#1e293b,55%,#09090b)] bg-[length:200%_100%] animate-shimmer" />
			<Tooltip id="home-tooltip" place="top" style={{ zIndex: 9999 }} />
			<main className="relative z-10 flex flex-col items-center justify-center w-full max-w-4xl px-4 text-center">
				<h1 className="text-4xl sm:text-5xl md:text-6xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-100 to-neutral-500 py-4">
					{getGreeting()}, {userDetails?.given_name || "User"}
				</h1>
				<p className="mt-2 mb-12 text-base md:text-lg text-neutral-400">
					How can I help you today?
				</p>
				<CommandBar
					prompt={prompt}
					setPrompt={setPrompt}
					onSend={handleSendCommand}
					isSending={isSending}
				/>
				<RevolvingProTip onTipClick={handleTipClick} />
			</main>
		</div>
	)
}

export default HomePage
