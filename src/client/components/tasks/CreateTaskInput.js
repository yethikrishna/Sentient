"use client"
import React, { useState, useRef, useEffect } from "react"
import { IconLoader, IconSend } from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { BorderTrail } from "@components/ui/border-trail"
import { TextLoop } from "@components/ui/TextLoop"
import toast from "react-hot-toast"

const CreateTaskInput = ({ onTaskAdded, prompt, setPrompt }) => {
	const [isSaving, setIsSaving] = useState(false)
	const textareaRef = useRef(null)

	useEffect(() => {
		const textarea = textareaRef.current
		if (textarea) {
			textarea.style.height = "auto"
			textarea.style.height = `${Math.min(textarea.scrollHeight, 100)}px`
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
		<div className="p-4 flex-shrink-0 bg-transparent">
			<div
				className={cn(
					"relative flex bg-brand-black rounded-full p-1 transition-all overflow-hidden min-h-[50px]"
				)}
			>
				<BorderTrail size={100} className="bg-brand-orange px-4" />
				<div
					className={cn(
						"relative flex gap-2 items-stretch bg-transparent p-1 transition-all w-full"
					)}
				>
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
						className="w-full rounded-l-full bg-transparent text-white placeholder-transparent border-1 border-brand-orange focus:ring-0 focus:ring-brand-black text-sm z-10 overflow-y-auto self-stretch py-2"
					/>
					{!prompt && (
						<div className="absolute top-1/2 left-4 -translate-y-1/2 text-neutral-500 pointer-events-none z-0">
							<TextLoop className="text-sm px-2">
								<span>Create a task...</span>
								<span>
									Summarize my unread emails from today
								</span>
								<span>
									Draft a follow-up to the project proposal
								</span>
								<span>
									Schedule a meeting with the design team
								</span>
							</TextLoop>
						</div>
					)}
					<button
						onClick={handleAddTask}
						disabled={isSaving || !prompt.trim()}
						className="p-3 bg-brand-orange rounded-r-full h-full text-brand-black disabled:opacity-50 hover:bg-opacity-80 transition-colors z-10 flex-shrink-0"
					>
						{isSaving ? (
							<IconLoader size={18} className="animate-spin" />
						) : (
							<IconSend size={18} />
						)}
					</button>
				</div>
			</div>
		</div>
	)
}

export default CreateTaskInput
