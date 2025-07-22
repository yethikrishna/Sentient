"use client"

import React, { useState } from "react"
import toast from "react-hot-toast"
import { motion } from "framer-motion"
import { IconX, IconLoader, IconSparkles, IconUser } from "@tabler/icons-react"
import { cn } from "@utils/cn"

const AddTaskModal = ({ onClose, onTaskAdded }) => {
	const [prompt, setPrompt] = useState("")
	const [assignee, setAssignee] = useState("ai") // 'ai' or 'user'
	const [isProcessing, setIsProcessing] = useState(false)

	const handleAddTask = async () => {
		if (!prompt.trim()) {
			toast.error("Please describe the task.")
			return
		}

		setIsProcessing(true)
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
			toast.success(data.message || "Task added!")
			onTaskAdded()
			onClose()
		} catch (error) {
			toast.error(`Error: ${error.message}`)
		} finally {
			setIsProcessing(false)
		}
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={onClose}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-lg border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-6 flex-shrink-0">
					<h2 className="text-xl font-semibold text-white">
						Add a New Task
					</h2>
					<button
						onClick={onClose}
						className="p-1 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
					>
						<IconX size={20} />
					</button>
				</div>

				<div className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-6">
					<div>
						<label
							htmlFor="task-prompt"
							className="block text-sm font-medium text-gray-300 mb-2"
						>
							What needs to be done?
						</label>
						<textarea
							id="task-prompt"
							value={prompt}
							onChange={(e) => setPrompt(e.target.value)}
							rows={4}
							className="w-full p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg transition-colors focus:border-[var(--color-accent-blue)] focus:ring-0"
							placeholder="e.g., Send a follow-up email to the new client about the proposal by tomorrow afternoon"
							autoFocus
						/>
					</div>

					<div>
						<label className="block text-sm font-medium text-gray-300 mb-2">
							Assign to
						</label>
						<div className="flex gap-2 p-1 bg-neutral-800/50 rounded-lg border border-neutral-700">
							<button
								onClick={() => setAssignee("ai")}
								className={cn(
									"flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm transition-colors",
									assignee === "ai"
										? "bg-[var(--color-accent-blue)] text-white"
										: "hover:bg-neutral-700"
								)}
							>
								<IconSparkles size={16} /> Sentient
							</button>
							<button
								onClick={() => setAssignee("user")}
								className={cn(
									"flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm transition-colors",
									assignee === "user"
										? "bg-[var(--color-accent-blue)] text-white"
										: "hover:bg-neutral-700"
								)}
							>
								<IconUser size={16} /> Me
							</button>
						</div>
						<p className="text-xs text-neutral-500 mt-2 px-1">
							{assignee === "ai"
								? "Sentient will create a plan and execute this task for you."
								: "This task will be added to your to-do list for you to complete."}
						</p>
					</div>
				</div>

				<div className="mt-6 pt-4 border-t border-[var(--color-primary-surface-elevated)] flex justify-end gap-4 flex-shrink-0">
					<button
						type="button"
						onClick={onClose}
						className="py-2.5 px-6 rounded-lg bg-dark-surface-elevated hover:bg-dark-surface text-sm transition-colors"
					>
						Cancel
					</button>
					<button
						onClick={handleAddTask}
						disabled={isProcessing}
						className="py-2.5 px-6 rounded-lg bg-sentient-blue hover:bg-sentient-blue-dark text-sm flex items-center gap-2 disabled:opacity-50 transition-colors"
					>
						{isProcessing && (
							<IconLoader size={16} className="animate-spin" />
						)}
						{isProcessing ? "Adding..." : "Add Task"}
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

export default AddTaskModal
