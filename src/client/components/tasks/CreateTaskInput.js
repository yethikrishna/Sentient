"use client"
import React, { useState, useRef, useEffect } from "react"
import { IconPlus, IconLoader } from "@tabler/icons-react"
import { TextLoop } from "@components/ui/TextLoop"
import toast from "react-hot-toast"

const CreateTaskInput = ({ onTaskAdded, prompt, setPrompt }) => {
	const [isSaving, setIsSaving] = useState(false)
	const textareaRef = useRef(null)

	useEffect(() => {
		const textarea = textareaRef.current
		if (textarea) {
			textarea.style.height = "auto"
			const scrollHeight = textarea.scrollHeight
			textarea.style.height = `${scrollHeight > 120 ? 120 : scrollHeight}px`
		}
	}, [prompt])

	const handleAddTask = async () => {
		if (!prompt.trim()) {
			toast.error("Please describe the task.")
			return
		}
		setIsSaving(true)
		try {
			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ prompt, assignee: "ai" })
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to add task")
			toast.success(data.message || "Task added!")
			setPrompt("")
			onTaskAdded()
		} catch (error) {
			toast.error(`Error: ${error.message}`)
		} finally {
			setIsSaving(false)
		}
	}

	return (
		<div className="p-4 border-t border-neutral-800 flex-shrink-0">
			<div className="relative flex items-end bg-neutral-900 border border-neutral-700 rounded-lg p-1">
				<textarea
					ref={textareaRef}
					value={prompt}
					onChange={(e) => setPrompt(e.target.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && !e.shiftKey) {
							e.preventDefault()
							handleAddTask()
						}
					}}
					placeholder=" "
					className="w-full bg-transparent text-white placeholder-transparent resize-none focus:ring-0 focus:outline-none p-2 custom-scrollbar"
					rows={1}
					style={{ maxHeight: "120px" }}
				/>
				{!prompt && (
					<div className="absolute top-1/2 left-3 -translate-y-1/2 text-neutral-500 pointer-events-none">
						<TextLoop className="text-sm font-mono">
							<span>Create a task...</span>
							<span>Summarize my unread emails from today</span>
							<span>
								Draft a follow-up to the project proposal
							</span>
							<span>Schedule a meeting with the design team</span>
						</TextLoop>
					</div>
				)}
				<button
					onClick={handleAddTask}
					disabled={isSaving || !prompt.trim()}
					className="p-2.5 bg-sentient-blue rounded-md text-white disabled:opacity-50 hover:bg-sentient-blue-dark transition-colors"
				>
					{isSaving ? (
						<IconLoader size={18} className="animate-spin" />
					) : (
						<IconPlus size={18} />
					)}
				</button>
			</div>
		</div>
	)
}

export default CreateTaskInput
