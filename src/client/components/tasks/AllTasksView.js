"use client"

import React, { useState, useMemo, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { format, parseISO } from "date-fns"
import {
	IconSparkles,
	IconUser,
	IconPencil,
	IconTrash,
	IconCircleCheck,
	IconPlus,
	IconRepeat,
	IconLoader
} from "@tabler/icons-react"
import { taskStatusColors, priorityMap } from "./constants"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"
import CollapsibleSection from "./CollapsibleSection"

const InlineNewTaskCard = ({ onTaskAdded }) => {
	const [prompt, setPrompt] = useState("")
	const [assignee, setAssignee] = useState("user")
	const [isSaving, setIsSaving] = useState(false)
	const inputRef = useRef(null)

	// Auto-resize textarea
	useEffect(() => {
		inputRef.current?.focus()
		const textarea = inputRef.current
		if (textarea) {
			textarea.style.height = "auto"
			const scrollHeight = textarea.scrollHeight
			textarea.style.height = `${scrollHeight}px`
		}
	}, [prompt])

	const handleSave = async () => {
		if (!prompt.trim()) {
			toast.error("Please provide a task description.")
			return
		}
		setIsSaving(true)
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
			onTaskAdded(true)
		} catch (error) {
			toast.error(error.message)
			onTaskAdded(false)
		} finally {
			setIsSaving(false)
		}
	}

	const handleCancel = () => {
		onTaskAdded(false)
	}

	const handleKeyDown = (e) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault()
			handleSave()
		}
		if (e.key === "Escape") {
			e.preventDefault()
			handleCancel()
		}
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="bg-[var(--color-primary-surface)] p-4 rounded-lg border border-[var(--color-accent-blue)]"
		>
			<textarea
				ref={inputRef}
				value={prompt}
				onChange={(e) => setPrompt(e.target.value)}
				onKeyDown={handleKeyDown}
				placeholder="What needs to be done?"
				className="w-full bg-transparent text-white placeholder-neutral-500 resize-none focus:ring-0 focus:outline-none mb-3 font-medium"
				rows={1}
			/>
			<div className="flex justify-between items-center mt-3 pt-3 border-t border-[var(--color-primary-surface-elevated)]">
				<div className="flex items-center gap-4">
					<button
						onClick={() =>
							setAssignee(assignee === "user" ? "ai" : "user")
						}
						className="flex items-center gap-1.5 text-neutral-400 hover:text-white transition-colors text-xs"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content={`Assign to: ${
							assignee === "ai" ? "AI" : "Me"
						}`}
					>
						{assignee === "ai" ? (
							<IconSparkles
								size={14}
								className="text-sentient-blue"
							/>
						) : (
							<IconUser size={14} />
						)}
						<span>{assignee === "ai" ? "Sentient" : "Me"}</span>
					</button>
				</div>
				<div className="flex items-center gap-2">
					<button
						onClick={handleCancel}
						className="text-neutral-400 hover:text-white text-xs font-semibold py-1 px-3 rounded-md hover:bg-neutral-700 transition-colors"
					>
						Cancel
					</button>
					<button
						onClick={handleSave}
						disabled={isSaving || !prompt.trim()}
						className="bg-sentient-blue hover:bg-sentient-blue-dark text-white text-xs font-semibold py-1 px-3 rounded-md disabled:opacity-50 flex items-center gap-1"
					>
						{isSaving ? (
							<IconLoader size={14} className="animate-spin" />
						) : (
							"Add Task"
						)}
					</button>
				</div>
			</div>
		</motion.div>
	)
}

const TaskListItem = ({
	task,
	onViewDetails,
	onMarkComplete,
	onAssigneeChange,
	activeTab
}) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	const assigneeDisplay = useMemo(() => {
		if (task.assignee === "user" && task.status === "pending") {
			return (
				<button
					onClick={(e) => {
						e.stopPropagation()
						onAssigneeChange(task.task_id, "ai")
					}}
					className="flex items-center gap-1.5 text-neutral-400 hover:text-white transition-colors"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Assign to AI"
				>
					<IconUser size={14} />
					<span>Me</span>
				</button>
			)
		}
		if (task.assignee === "ai") {
			return (
				<div
					className="flex items-center gap-1.5 text-neutral-400"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Assigned to AI"
				>
					<IconSparkles size={14} className="text-sentient-blue" />
					<span>Sentient</span>
				</div>
			)
		}
		return (
			<div className="flex items-center gap-1.5 text-neutral-500">
				<IconSparkles size={14} />
				<span>Sentient</span>
			</div>
		)
	}, [task, onAssigneeChange])

	const dueDate =
		task.schedule?.run_at && activeTab !== "recurring"
			? format(parseISO(task.schedule.run_at), "MMM d, yyyy")
			: "No Due Date"

	return (
		<motion.div
			layout
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={(e) => {
				if (e.target.closest("button")) return
				onViewDetails(task)
			}}
			className="bg-[var(--color-primary-surface)] p-4 rounded-lg border border-[var(--color-primary-surface-elevated)] hover:border-[var(--color-accent-blue)] transition-all group relative cursor-pointer"
		>
			<div className="flex justify-between items-start gap-4">
				<div className="flex items-start gap-2 flex-1 min-w-0">
					<p className="font-medium text-[var(--color-text-primary)]">
						{task.description}
					</p>
					<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 pt-0.5">
						{task.assignee === "user" &&
							task.status === "pending" && (
								<button
									onClick={(e) => {
										e.stopPropagation()
										onMarkComplete(task.task_id)
									}}
									className="p-1.5 text-neutral-400 hover:text-green-400 hover:bg-neutral-700 rounded-md transition-colors"
									data-tooltip-id="tasks-tooltip"
									data-tooltip-content="Mark Complete"
								>
									<IconCircleCheck size={16} />
								</button>
							)}
					</div>
				</div>
				<div className="flex items-center gap-2 text-xs flex-shrink-0">
					<statusInfo.icon
						className={cn("h-4 w-4", statusInfo.color)}
					/>
					<span className={cn(statusInfo.color, "font-medium")}>
						{statusInfo.label}
					</span>
				</div>
			</div>

			<div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mt-4 pt-3 border-t border-[var(--color-primary-surface-elevated)] text-xs text-neutral-400">
				<div className="flex items-center gap-4">
					{assigneeDisplay}
					{activeTab !== "recurring" && (
						<span className="font-medium text-neutral-300">
							{dueDate}
						</span>
					)}
				</div>
				<span className={cn("font-medium", priorityInfo.color)}>
					{priorityInfo.label}
				</span>
			</div>
		</motion.div>
	)
}

const AllTasksView = ({
	tasks,
	onViewDetails,
	onMarkComplete,
	onAssigneeChange,
	activeTab,
	groupBy,
	onTabChange,
	onGroupChange,
	isAddingNewTask,
	onAddTask,
	onTaskAdded
}) => {
	const [sortConfig, setSortConfig] = useState({
		key: "priority",
		direction: "ascending"
	})
	const [openSections, setOpenSections] = useState({})

	const handleToggleSection = (title) => {
		setOpenSections((prev) => ({
			...prev,
			[title]: !(prev[title] ?? true) // Defaults to open, so first toggle closes it
		}))
	}

	useEffect(() => {
		if (isAddingNewTask && groupBy === "status") {
			setOpenSections((prev) => ({ ...prev, Planning: true }))
		}
	}, [isAddingNewTask, groupBy])
	const processedTasks = useMemo(() => {
		const filteredTasks =
			activeTab === "oneTime"
				? tasks.filter((t) => t.schedule?.type !== "recurring")
				: tasks.filter((t) => t.schedule?.type === "recurring")

		let sortedTasks = [...filteredTasks]
		sortedTasks.sort((a, b) => {
			const { key, direction } = sortConfig
			let valA, valB

			switch (key) {
				case "assignee":
					valA = a.assignee || "user"
					valB = b.assignee || "user"
					break
				case "dueDate":
					valA = a.schedule?.run_at
						? parseISO(a.schedule.run_at).getTime()
						: Infinity
					valB = b.schedule?.run_at
						? parseISO(b.schedule.run_at).getTime()
						: Infinity
					break
				case "priority":
					valA = a.priority ?? 2
					valB = b.priority ?? 2
					break
				default:
					return 0
			}

			if (valA < valB) return direction === "ascending" ? -1 : 1
			if (valA > valB) return direction === "ascending" ? 1 : -1

			// Secondary sort by due date if priorities are equal, and vice-versa
			if (key !== "dueDate") {
				const dateA = a.schedule?.run_at
					? parseISO(a.schedule.run_at).getTime()
					: Infinity
				const dateB = b.schedule?.run_at
					? parseISO(b.schedule.run_at).getTime()
					: Infinity
				return dateA - dateB
			}
			return 0
		})

		// Group logic
		if (groupBy === "none") {
			return { "All Tasks": sortedTasks }
		}

		const grouped = sortedTasks.reduce((acc, task) => {
			let key
			if (groupBy === "status") {
				key = taskStatusColors[task.status]?.label || "Unknown"
			}
			if (!acc[key]) {
				acc[key] = []
			}
			acc[key].push(task)
			return acc
		}, {})

		// Now sort the tasks within each group by priority
		for (const key in grouped) {
			grouped[key].sort((a, b) => {
				const priorityA = a.priority ?? 2
				const priorityB = b.priority ?? 2
				return priorityA - priorityB
			})
		}

		return grouped
	}, [tasks, activeTab, groupBy, sortConfig])

	const orderedGroupNames = useMemo(() => {
		const groupOrder = [
			"planning",
			"pending",
			"approval_pending",
			"clarification_pending",
			"processing",
			"active",
			"completed",
			"error",
			"cancelled",
			"archived"
		]
		const groupNames = Object.keys(processedTasks).sort((a, b) => {
			const statusA =
				Object.keys(taskStatusColors).find(
					(key) => taskStatusColors[key].label === a
				) || ""
			const statusB =
				Object.keys(taskStatusColors).find(
					(key) => taskStatusColors[key].label === b
				) || ""
			return groupOrder.indexOf(statusA) - groupOrder.indexOf(statusB)
		})
		return groupNames
	}, [processedTasks])

	const isRecurring = activeTab === "recurring"

	return (
		<div className="h-full flex flex-col">
			<div className="flex items-center justify-between p-6 border-b border-[var(--color-primary-surface)]">
				<div className="flex items-center gap-6">
					<div className="flex items-center gap-2">
						<label className="text-sm text-[var(--color-text-secondary)] font-medium">
							Show:
						</label>
						<select
							value={activeTab}
							onChange={(e) => onTabChange(e.target.value)}
							className="bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent-blue)] outline-none"
						>
							<option value="oneTime">One-time</option>
							<option value="recurring">Recurring</option>
						</select>
					</div>
					<div className="flex items-center gap-2">
						<label className="text-sm text-[var(--color-text-secondary)] font-medium">
							Group by:
						</label>
						<select
							value={groupBy}
							onChange={(e) => onGroupChange(e.target.value)}
							className="bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent-blue)] outline-none"
						>
							<option value="status">Status</option>
							<option value="none">None</option>
						</select>
					</div>
				</div>
				<button
					onClick={onAddTask}
					className="flex items-center gap-2 py-2 px-4 rounded-lg bg-sentient-blue hover:bg-sentient-blue-dark text-white text-sm font-medium transition-colors"
				>
					<IconPlus size={16} /> Add Task
				</button>
			</div>

			<div className="flex-1 flex flex-col overflow-hidden">
				<div className="flex-1 overflow-y-auto custom-scrollbar px-6 pt-6 pb-6">
					{Object.keys(processedTasks).length > 0 ||
					isAddingNewTask ? (
						<AnimatePresence>
							{orderedGroupNames.map((groupName) => {
								const groupTasks =
									processedTasks[groupName] || []
								if (
									groupTasks.length === 0 &&
									!(
										isAddingNewTask &&
										groupName === "Planning"
									)
								)
									return null
								return (
									<React.Fragment key={groupName}>
										{groupBy !== "none" ? (
											<CollapsibleSection
												title={groupName}
												count={groupTasks.length}
												isOpen={
													openSections[groupName] ??
													true
												}
												onToggle={() =>
													handleToggleSection(
														groupName
													)
												}
											>
												<div className="space-y-3">
													{isAddingNewTask &&
														groupName ===
															"Planning" && (
															<InlineNewTaskCard
																onTaskAdded={
																	onTaskAdded
																}
															/>
														)}
													{groupTasks.map((task) => (
														<TaskListItem
															key={task.task_id}
															task={task}
															onViewDetails={
																onViewDetails
															}
															onMarkComplete={
																onMarkComplete
															}
															onAssigneeChange={
																onAssigneeChange
															}
															activeTab={
																activeTab
															}
														/>
													))}
												</div>
											</CollapsibleSection>
										) : (
											<div className="space-y-3">
												{isAddingNewTask && (
													<InlineNewTaskCard
														onTaskAdded={
															onTaskAdded
														}
													/>
												)}
												{groupTasks.map((task) => (
													<TaskListItem
														key={task.task_id}
														task={task}
														onViewDetails={
															onViewDetails
														}
														onMarkComplete={
															onMarkComplete
														}
														onAssigneeChange={
															onAssigneeChange
														}
														activeTab={activeTab}
													/>
												))}
											</div>
										)}
									</React.Fragment>
								)
							})}
							{isAddingNewTask &&
								groupBy === "status" &&
								!processedTasks["Planning"] && (
									<CollapsibleSection
										title="Planning"
										count={0}
										isOpen={
											openSections["Planning"] ?? true
										}
										onToggle={() =>
											handleToggleSection("Planning")
										}
									>
										<InlineNewTaskCard
											onTaskAdded={onTaskAdded}
										/>
									</CollapsibleSection>
								)}
						</AnimatePresence>
					) : (
						<div className="flex items-center justify-center h-full text-center p-8">
							<div>
								<div className="text-4xl mb-3 text-[var(--color-text-muted)]">
									📝
								</div>
								<div className="text-lg font-medium text-[var(--color-text-primary)] mb-2">
									No {isRecurring ? "recurring" : "one-time"}{" "}
									tasks found
								</div>
								<div className="text-sm text-[var(--color-text-secondary)]">
									{!isRecurring
										? "Create your first task above!"
										: "Set up recurring workflows to automate your tasks."}
								</div>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	)
}

export default AllTasksView
