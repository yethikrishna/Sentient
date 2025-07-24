"use client"

import React, { useState, useEffect, useRef } from "react"
import toast from "react-hot-toast"
import { motion } from "framer-motion"
import { IconLoader } from "@tabler/icons-react"

const InlineNewTaskCard = ({ onTaskAdded }) => {
	const [prompt, setPrompt] = useState("")
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
				body: JSON.stringify({ prompt })
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to add task")
			toast.success("Task added.")
			onTaskAdded() // Refresh task list
			setPrompt("") // Clear input for next task
			textareaRef.current?.focus() // Refocus input
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsAdding(false)
		}
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
				}}
			/>
			<div className="flex justify-end items-center">
				<div className="flex items-center">
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
