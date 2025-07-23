"use client"

import React, { useState, useEffect, useRef } from "react"
import toast from "react-hot-toast"
import { motion } from "framer-motion"
import { IconSparkles, IconUser, IconLoader } from "@tabler/icons-react"
import { cn } from "@utils/cn"

const NewTaskCard = ({ onTaskAdded }) => {
	const [prompt, setPrompt] = useState("")
	const [assignee, setAssignee] = useState("user")
	const [isSaving, setIsSaving] = useState(false)
	const inputRef = useRef(null)

	useEffect(() => {
		inputRef.current?.focus()
		inputRef.current?.scrollIntoView({
			behavior: "smooth",
			block: "center"
		})
	}, [])

	const handleSave = async () => {
		if (!prompt.trim()) {
			toast.error("Please enter a task description.")
			return
		}
		setIsSaving(true)
		try {
			// New tasks created by the user are 'pending' if assigned to self, or 'planning' if assigned to AI
			const status = assignee === "ai" ? "planning" : "pending"
			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ prompt, assignee, status })
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to add task")

			toast.success("Task added.")
			onTaskAdded(true) // Signal success to parent
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSaving(false)
		}
	}

	const handleCancel = () => {
		onTaskAdded(false) // Signal cancellation to parent
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: -20 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, y: -20 }}
			className="bg-sentient-blue/10 p-4 rounded-lg border-2 border-dashed border-sentient-blue/50 space-y-3"
		>
			<textarea
				ref={inputRef}
				value={prompt}
				onChange={(e) => setPrompt(e.target.value)}
				onKeyDown={(e) => {
					if (e.key === "Enter" && !e.shiftKey) {
						e.preventDefault()
						handleSave()
					}
					if (e.key === "Escape") {
						handleCancel()
					}
				}}
				placeholder="What needs to be done?"
				className="w-full bg-transparent text-white placeholder-neutral-400 resize-none outline-none text-sm font-medium"
				rows={2}
			/>
			<div className="flex justify-between items-center">
				<div className="flex gap-1 p-1 bg-neutral-900/50 rounded-lg border border-neutral-700">
					<button
						onClick={() => setAssignee("ai")}
						className={cn(
							"flex items-center gap-1.5 py-1 px-3 rounded-md text-xs transition-colors",
							assignee === "ai"
								? "bg-sentient-blue text-white"
								: "hover:bg-neutral-700 text-neutral-300"
						)}
					>
						<IconSparkles size={14} /> AI
					</button>
					<button
						onClick={() => setAssignee("user")}
						className={cn(
							"flex items-center gap-1.5 py-1 px-3 rounded-md text-xs transition-colors",
							assignee === "user"
								? "bg-sentient-blue text-white"
								: "hover:bg-neutral-700 text-neutral-300"
						)}
					>
						<IconUser size={14} /> Me
					</button>
				</div>
				<div className="flex items-center gap-2">
					<button
						onClick={handleCancel}
						className="py-1.5 px-4 rounded-md bg-neutral-700 hover:bg-neutral-600 text-white text-xs font-medium transition-colors"
					>
						Cancel
					</button>
					<button
						onClick={handleSave}
						disabled={isSaving}
						className="py-1.5 px-4 rounded-md bg-sentient-blue hover:bg-sentient-blue-dark text-white text-xs font-medium transition-colors flex items-center gap-2 disabled:opacity-60"
					>
						{isSaving && (
							<IconLoader size={14} className="animate-spin" />
						)}
						Save
					</button>
				</div>
			</div>
		</motion.div>
	)
}

export default NewTaskCard
