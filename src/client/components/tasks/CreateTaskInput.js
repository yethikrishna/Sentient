"use client"
import React, { useState, useRef, useEffect } from "react"
import { IconLoader, IconSend, IconUsersGroup } from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { BorderTrail } from "@components/ui/border-trail"
import { TextLoop } from "@components/ui/TextLoop"
import toast from "react-hot-toast"

const CreateTaskInput = ({ onTaskAdded, prompt, setPrompt }) => {
	const [isSwarmMode, setIsSwarmMode] = useState(false)
	const [isSaving, setIsSaving] = useState(false)
	const textareaRef = useRef(null)

	useEffect(() => {
		const textarea = textareaRef.current
		if (textarea) {
			textarea.style.height = "auto"
			textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`
		}
	}, [prompt])

	const handleAddTask = async () => {
		setIsSaving(true)
		let payload = {}

		if (!prompt.trim()) {
			toast.error("Please describe the task.")
			setIsSaving(false)
			return
		}
		payload = {
			prompt: prompt.trim(),
			is_swarm: isSwarmMode
		}

		try {
			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload)
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to add task")

			// Create a temporary task object for optimistic UI
			const tempTask = {
				task_id: data.task_id,
				name: prompt.trim(),
				description: prompt.trim(),
				status: "planning",
				assignee: "ai",
				priority: 1,
				plan: [],
				runs: [],
				schedule: null,
				enabled: true,
				original_context: { source: "manual_creation" },
				created_at: new Date().toISOString(),
				updated_at: new Date().toISOString(),
				chat_history: [],
				next_execution_at: null,
				last_execution_at: null,
				task_type: isSwarmMode ? "swarm" : "single",
				swarm_details: isSwarmMode
					? {
							goal: prompt,
							items: [],
							total_agents: 0,
							completed_agents: 0,
							progress_updates: [],
							aggregated_results: []
						}
					: null
			}

			toast.success(
				data.message ||
					(isSwarmMode ? "Swarm task initiated!" : "Task added!")
			)
			setPrompt("")
			// Pass the temporary task object to the parent for optimistic update
			onTaskAdded(tempTask)
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
					"relative flex bg-brand-black p-1 transition-all overflow-hidden",
					"rounded-full min-h-[50px]"
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
						<div className="absolute top-1/2 left-4 right-12 -translate-y-1/2 text-neutral-500 pointer-events-none z-0 overflow-hidden">
							<TextLoop className="text-sm px-2 whitespace-normal md:whitespace-nowrap">
								<span>
									{isSwarmMode
										? "Describe a swarm task..."
										: "Create a task..."}
								</span>
								<span>
									Summarize my unread emails from today
								</span>
								<span>
									Draft a follow-up to the project proposal
								</span>
								<span>
									{isSwarmMode
										? "Research these topics: AI, ML, and Data Science"
										: "Schedule a meeting with the design team"}
								</span>
							</TextLoop>
						</div>
					)}
					<div className={cn("flex items-center gap-2 z-10")}>
						<button
							onClick={() => setIsSwarmMode(!isSwarmMode)}
							className={cn(
								"p-3 rounded-full h-full transition-colors",
								isSwarmMode
									? "bg-blue-600 text-white"
									: "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
							)}
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content={
								isSwarmMode
									? "Switch to Single Task Mode"
									: "Switch to Swarm Mode"
							}
						>
							<IconUsersGroup size={18} />
						</button>
						<button
							onClick={handleAddTask}
							disabled={isSaving || !prompt.trim()}
							className="p-3 bg-brand-orange rounded-full h-full text-brand-black disabled:opacity-50 hover:bg-opacity-80 transition-colors flex-shrink-0"
						>
							{isSaving ? (
								<IconLoader
									size={18}
									className="animate-spin"
								/>
							) : (
								<IconSend size={18} />
							)}
						</button>
					</div>
				</div>
			</div>
		</div>
	)
}

export default CreateTaskInput
