// A new file: src/client/components/tasks/AddTaskModal.js
"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import { IconX, IconLoader } from "@tabler/icons-react"
import ScheduleEditor from "@components/tasks/ScheduleEditor"

const AddTaskModal = ({ onClose, onTaskAdded, initialDate }) => {
	const [description, setDescription] = useState("")
	const [schedule, setSchedule] = useState({
		type: "once",
		run_at: initialDate || null
	})
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleSubmit = async (e) => {
		e.preventDefault()
		if (!description.trim()) {
			toast.error("Please enter a task description.")
			return
		}

		setIsSubmitting(true)
		try {
			const payload = {
				description,
				priority: 1, // Default priority for now
				schedule
			}
			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload)
			})

			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to add task")
			}
			toast.success("Task created! I'll start planning it out.")
			onTaskAdded() // This will trigger a refresh on the tasks page
			onClose()
		} catch (error) {
			toast.error(`Error: ${error.message}`)
		} finally {
			setIsSubmitting(false)
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
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-2xl border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-6 flex-shrink-0">
					<h2 className="text-xl font-semibold text-white">
						Add New Task
					</h2>
					<button
						onClick={onClose}
						className="p-1 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
					>
						<IconX size={20} />
					</button>
				</div>
				<form
					onSubmit={handleSubmit}
					className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-6"
				>
					<div>
						<label
							htmlFor="task-description"
							className="block text-sm font-medium text-gray-300 mb-2"
						>
							What needs to be done?
						</label>
						<textarea
							id="task-description"
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							rows={3}
							className="w-full p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg transition-colors focus:border-[var(--color-accent-blue)]"
							placeholder="e.g., Send a follow-up email to the new client about the proposal by tomorrow afternoon"
							autoFocus
						/>
					</div>
					<div>
						<label className="block text-sm font-medium text-gray-300 mb-2">
							Scheduling
						</label>
						<ScheduleEditor
							schedule={schedule}
							setSchedule={setSchedule}
						/>
					</div>
				</form>
				<div className="mt-6 pt-4 border-t border-[var(--color-primary-surface-elevated)] flex justify-end gap-4 flex-shrink-0">
					<button
						type="button"
						onClick={onClose}
						className="py-2.5 px-6 rounded-lg bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-sm transition-colors"
					>
						Cancel
					</button>
					<button
						type="submit"
						onClick={handleSubmit}
						disabled={isSubmitting || !description.trim()}
						className="py-2.5 px-6 rounded-lg bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-sm flex items-center gap-2 disabled:opacity-50 transition-colors"
					>
						{isSubmitting && (
							<IconLoader size={16} className="animate-spin" />
						)}
						{isSubmitting ? "Adding..." : "Add Task"}
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

export default AddTaskModal
