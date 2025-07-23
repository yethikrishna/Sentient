"use client"

import React, { useState, useEffect, useRef } from "react"
import toast from "react-hot-toast"
import { motion } from "framer-motion"
import { IconSparkles, IconUser, IconLoader } from "@tabler/icons-react"

const InlineNewTaskCard = ({ onTaskAdded }) => {
	const [prompt, setPrompt] = useState("")
	const [assignee, setAssignee] = useState("user")
	const [isAdding, setIsAdding] = useState(false)
	const textareaRef = useRef(null)

	useEffect(() => {
		textareaRef.current?.focus()
	}, [])

	useEffect(() => {
		const textarea = textareaRef.current
		if (textarea) {
			textarea.style.height = "auto"
			textarea.style.height = `${textarea.scrollHeight}px`
		}
	}, [prompt])

	const handleAddTask = async () => {
		if (!prompt.trim() || isAdding) return
		setIsAdding(true)
		try {
			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ prompt, assignee, status: "planning" })
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to add task")
			toast.success("Task added.")
			onTaskAdded(true) // Indicate success
		} catch (error) {
			toast.error(error.message)
			onTaskAdded(false) // Indicate failure
		} finally {
			setIsAdding(false)
		}
	}

	const handleCancel = () => {
		onTaskAdded(false) // Just close it without refetching
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: -20 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, scale: 0.95 }}
			className="bg-blue-500/10 p-3 rounded-lg border border-blue-500/50 space-y-3 mb-3"
		>
			<textarea
				ref={textareaRef}
				value={prompt}
				onChange={(e) => setPrompt(e.target.value)}
				placeholder="What needs to be done?"
				className="w-full bg-transparent text-white placeholder-neutral-400 resize-none outline-none font-medium text-sm"
				rows={1}
				onKeyDown={(e) => {
					if (e.key === "Enter" && !e.shiftKey) {
						e.preventDefault()
						handleAddTask()
					}
					if (e.key === "Escape") {
						handleCancel()
					}
				}}
			/>
			<div className="flex justify-between items-center">
				<div className="flex items-center gap-1">
					<button
						onClick={() =>
							setAssignee(assignee === "user" ? "ai" : "user")
						}
						className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-700/50 rounded-lg transition-colors text-xs flex items-center gap-1"
					>
						{assignee === "ai" ? (
							<IconSparkles size={14} />
						) : (
							<IconUser size={14} />
						)}
						<span>{assignee === "ai" ? "Sentient" : "Me"}</span>
					</button>
				</div>
				<div className="flex items-center gap-2">
					<button
						onClick={handleCancel}
						className="text-sm text-neutral-400 hover:text-white px-3 py-1.5 rounded-md hover:bg-neutral-700"
					>
						Cancel
					</button>
					<button
						onClick={handleAddTask}
						disabled={isAdding || !prompt.trim()}
						className="px-4 py-1.5 bg-sentient-blue hover:bg-sentient-blue-dark text-white rounded-md disabled:opacity-50 text-sm flex items-center gap-2"
					>
						{isAdding ? (
							<IconLoader size={16} className="animate-spin" />
						) : (
							"Add Task"
						)}
					</button>
				</div>
			</div>
		</motion.div>
	)
}

export default InlineNewTaskCard
