"use client"
import React, { useState, useRef, useEffect } from "react"
import { IconLoader, IconSend, IconUsersGroup } from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { BorderTrail } from "@components/ui/border-trail"
import { TextLoop } from "@components/ui/TextLoop"
import toast from "react-hot-toast"

const CreateTaskInput = ({
	onTaskAdded,
	prompt,
	setPrompt,
	isPro,
	onUpgradeClick
}) => {
	const [isSwarmMode, setIsSwarmMode] = useState(false)
	const [isSaving, setIsSaving] = useState(false)
	const [isExpanded, setIsExpanded] = useState(false)
	const textareaRef = useRef(null)

	useEffect(() => {
		const textarea = textareaRef.current
		if (textarea) {
			// Always reset to single line height first
			textarea.style.height = "44px" // Single line height

			let newHeight = "44px"
			let leftPadding = "1.5rem" // Default padding (pl-6)

			// Only expand if content requires it and there's actual content
			if (prompt.trim() && textarea.scrollHeight > 44) {
				newHeight = `${Math.min(textarea.scrollHeight, 150)}px`
				// Increase left padding for taller textareas to clear rounded corners
				leftPadding = "4rem" // Increased padding (pl-10)
				setIsExpanded(true)
			} else if (!prompt.trim()) {
				// If no content, ensure we stay at single line height
				newHeight = "44px"
				setIsExpanded(false)
			} else {
				// Content exists but fits in single line
				newHeight = "44px"
				setIsExpanded(false)
			}

			textarea.style.height = newHeight
			textarea.style.paddingLeft = leftPadding
		}
	}, [prompt])

	const handleToggleSwarmMode = () => {
		if (!isPro) {
			onUpgradeClick()
			return
		}
		setIsSwarmMode(!isSwarmMode)
	}

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
			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}))
				const error = new Error(errorData.error || "Failed to add task")
				error.status = response.status
				throw error
			}
			const data = await response.json()

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
			if (error.status === 429) {
				toast.error(
					error.message ||
						"You've reached your daily task limit for the free plan."
				)
				// Here, onUpgradeClick is passed as a prop from tasks/page.js
				// and it sets isUpgradeModalOpen to true.
				if (!isPro) {
					onUpgradeClick()
				}
			} else {
				toast.error(`Error: ${error.message}`)
			}
		} finally {
			setIsSaving(false)
		}
	}

	return (
		<div className="p-4 flex-shrink-0 bg-transparent">
			<div
				className={cn(
					"relative flex bg-brand-black p-1 transition-all overflow-hidden",
					"rounded-full min-h-[46px]"
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
							if (e.key === "Enter" && e.shiftKey) {
								// Allow new line on Shift+Enter
								return
							} else if (e.key === "Enter") {
								// Submit on Enter
								e.preventDefault()
								handleAddTask()
							}
						}}
						placeholder=" "
						className="w-full rounded-l-full bg-transparent text-white placeholder-transparent border-0 focus:ring-0 focus:outline-none text-sm z-10 resize-none leading-tight pr-4 py-3 min-h-[44px] max-h-[150px]"
						rows="1"
					/>

					{!prompt && (
						<div
							className={cn(
								"absolute top-1/2 -translate-y-1/2 text-neutral-500 pointer-events-none z-0 transition-all duration-200",
								isExpanded
									? "left-10 right-24"
									: "left-6 right-24"
							)}
						>
							<div className="overflow-hidden w-full">
								<TextLoop className="text-sm px-2 whitespace-nowrap">
									<span>
										{isSwarmMode
											? "Describe a swarm task..."
											: "Create a task..."}
									</span>
									<span className="hidden sm:inline">
										Summarize my unread emails from today
									</span>
									<span className="sm:hidden">
										Summarize my emails
									</span>
									<span className="hidden sm:inline">
										Draft a follow-up to the project
										proposal
									</span>
									<span className="sm:hidden">
										Draft a follow-up
									</span>
									<span>
										{isSwarmMode
											? "Research these topics: AI, ML, and Data Science"
											: "Schedule a meeting"}
									</span>
								</TextLoop>
							</div>
						</div>
					)}
					<div
						className={cn(
							"flex items-center gap-2 z-10 pr-1 flex-shrink-0"
						)}
					>
						<button
							onClick={handleToggleSwarmMode}
							className={cn(
								"p-3 rounded-full w-11 h-11 transition-colors flex items-center justify-center",
								isSwarmMode
									? "bg-blue-600 text-white"
									: "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
							)}
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content={
								isPro
									? isSwarmMode
										? "Switch to Single Task Mode"
										: "Switch to Swarm Mode (Parallel Agents)"
									: "Swarm Mode (Pro Feature)"
							}
						>
							<IconUsersGroup size={18} />
						</button>
						<button
							onClick={handleAddTask}
							disabled={isSaving || !prompt.trim()}
							className="p-3 bg-brand-orange rounded-full w-11 h-11 text-brand-black disabled:opacity-50 hover:bg-opacity-80 transition-colors flex-shrink-0 flex items-center justify-center"
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
