"use client"

import React, { useState, useMemo, useEffect } from "react"
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
	IconArrowUp,
	IconArrowDown,
	IconGitFork,
	IconSelector,
	IconLoader
} from "@tabler/icons-react"
import { taskStatusColors, priorityMap } from "./constants"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"

// New component for inline task adding
const QuickAddTask = ({ onTaskAdded }) => {
	const [prompt, setPrompt] = useState("")
	const [assignee, setAssignee] = useState("user") // 'user' or 'ai'
	const [isAdding, setIsAdding] = useState(false)
	const inputRef = React.useRef(null)

	// Auto-resize textarea
	useEffect(() => {
		const textarea = inputRef.current
		if (textarea) {
			textarea.style.height = "auto"
			const scrollHeight = textarea.scrollHeight
			textarea.style.height = `${scrollHeight}px`
		}
	}, [prompt])

	const handleAddTask = async () => {
		if (!prompt.trim() || isAdding) return

		setIsAdding(true)
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
			toast.success("Task added.")
			setPrompt("")
			onTaskAdded() // Refresh the list
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsAdding(false)
			// Refocus input for the next task
			inputRef.current?.focus()
		}
	}

	return (
		<div className="relative p-2 mb-4 bg-dark-surface rounded-lg border border-dark-surface-elevated focus-within:ring-2 focus-within:ring-sentient-blue transition-all">
			<textarea
				ref={inputRef}
				value={prompt}
				onChange={(e) => setPrompt(e.target.value)}
				onKeyDown={(e) => {
					if (e.key === "Enter" && !e.shiftKey) {
						e.preventDefault()
						handleAddTask()
					}
				}}
				placeholder="Add a new task for yourself or Sentient..."
				className="w-full bg-transparent p-2 pr-28 text-white placeholder-neutral-500 focus:ring-0 focus:outline-none resize-none max-h-48 custom-scrollbar"
				rows={1}
				disabled={isAdding}
			/>
			<div className="absolute top-1/2 right-3 -translate-y-1/2 flex items-center gap-2">
				<button
					onClick={() =>
						setAssignee(assignee === "user" ? "ai" : "user")
					}
					className="p-2 rounded-full hover:bg-dark-surface-elevated"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content={`Assign to: ${
						assignee === "ai" ? "AI" : "Me"
					}`}
				>
					{assignee === "ai" ? (
						<IconSparkles
							size={18}
							className="text-sentient-blue"
						/>
					) : (
						<IconUser size={18} className="text-neutral-400" />
					)}
				</button>
				<button
					onClick={handleAddTask}
					disabled={isAdding || !prompt.trim()}
					className="p-2 bg-sentient-blue rounded-full text-white disabled:opacity-50"
				>
					{isAdding ? (
						<IconLoader size={18} className="animate-spin" />
					) : (
						<IconPlus size={18} />
					)}
				</button>
			</div>
		</div>
	)
}

// Sortable Header component for table columns
const SortableHeader = ({
	title,
	sortKey,
	sortConfig,
	onSort,
	className = ""
}) => {
	const isSorting = sortConfig.key === sortKey
	const isAscending = isSorting && sortConfig.direction === "ascending"

	let IconComponent
	let iconClassName = "text-neutral-600"

	if (isSorting) {
		IconComponent = isAscending ? IconArrowUp : IconArrowDown
		iconClassName = "text-white"
	} else {
		IconComponent = IconSelector
	}

	return (
		<button
			onClick={() => onSort(sortKey)}
			className={cn(
				"flex items-center justify-center gap-1 font-bold text-neutral-400 hover:text-white transition-colors group",
				className
			)}
		>
			<span>{title}</span>
			<IconComponent
				size={16}
				className={cn(iconClassName, "group-hover:text-white")}
			/>
		</button>
	)
}

const TaskListItem = ({
	task,
	onViewDetails,
	onEditTask,
	onDeleteTask,
	onRerunTask,
	onMarkComplete,
	onAssigneeChange,
	originalTask,
	activeTab
}) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default

	const assigneeDisplay = useMemo(() => {
		if (task.assignee === "user" && task.status === "pending") {
			return (
				<button
					onClick={(e) => {
						e.stopPropagation()
						onAssigneeChange(task.task_id, "ai")
					}}
					className="p-1 rounded-full hover:bg-blue-500/20 group/assignee"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Assign to AI"
				>
					<IconUser
						size={18}
						className="text-neutral-400 group-hover/assignee:text-blue-400 transition-colors"
					/>
				</button>
			)
		}
		if (task.assignee === "ai") {
			return (
				<IconSparkles
					size={18}
					className="text-blue-400"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Assigned to AI"
				/>
			)
		}
		return <IconSparkles size={18} className="text-neutral-400" />
	}, [task, onAssigneeChange])

	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	const dueDate = task.schedule?.run_at
		? format(parseISO(task.schedule.run_at), "MMM d")
		: "No date"

	const gridTemplateColumns =
		activeTab === "oneTime"
			? "minmax(0, 1fr) 120px 120px 120px 150px"
			: "minmax(0, 1fr) 120px 120px 150px"

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
			className="grid items-center p-2 border-b border-dark-surface-elevated hover:bg-dark-surface cursor-pointer text-sm group"
			style={{ gridTemplateColumns }}
		>
			<div className="pr-4 font-medium">
				<div className="flex items-center gap-2">
					<div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
						{task.assignee === "user" &&
							task.status === "pending" && (
								<button
									onClick={(e) => {
										e.stopPropagation()
										onMarkComplete(task.task_id)
									}}
									className="p-1 rounded text-neutral-400 hover:bg-green-500/20 hover:text-green-400"
									data-tooltip-id="tasks-tooltip"
									data-tooltip-content="Mark Complete"
								>
									<IconCircleCheck size={14} />
								</button>
							)}
						<button
							onClick={(e) => {
								e.stopPropagation()
								onRerunTask(task.task_id)
							}}
							className="p-1 rounded text-neutral-400 hover:bg-dark-surface-elevated"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Rerun Task"
						>
							<IconRepeat size={14} />
						</button>
						<button
							onClick={(e) => {
								e.stopPropagation()
								onEditTask(task)
							}}
							className="p-1 rounded text-neutral-400 hover:bg-dark-surface-elevated"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Edit"
						>
							<IconPencil size={14} />
						</button>
						<button
							onClick={(e) => {
								e.stopPropagation()
								onDeleteTask(task.task_id)
							}}
							className="p-1 rounded text-neutral-400 hover:bg-red-500/20 hover:text-red-400"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Delete"
						>
							<IconTrash size={14} />
						</button>
					</div>
					<span className="truncate">{task.description}</span>
				</div>
				{originalTask && (
					<button
						onClick={(e) => {
							e.stopPropagation()
							onViewDetails(originalTask)
						}}
						className="flex items-center gap-1.5 text-xs text-neutral-400 hover:text-sentient-blue hover:underline mt-1 pl-2"
					>
						<IconGitFork size={12} />
						<span className="truncate">
							Change for: {originalTask.description}
						</span>
					</button>
				)}
			</div>
			<div className="flex items-center justify-center">
				{assigneeDisplay}
			</div>
			{activeTab === "oneTime" && (
				<div className="text-center text-neutral-400">{dueDate}</div>
			)}
			<div className={cn("text-center font-medium", priorityInfo.color)}>
				{priorityInfo.label}
			</div>
			<div className="flex items-center justify-center gap-2">
				<statusInfo.icon className={cn("h-4 w-4", statusInfo.color)} />
				<span className={cn(statusInfo.color)}>{statusInfo.label}</span>
			</div>
		</motion.div>
	)
}

const AllTasksView = ({
	tasks,
	onViewDetails,
	onEditTask,
	onDeleteTask,
	onRerunTask,
	onMarkComplete,
	onAssigneeChange,
	onTaskAdded
}) => {
	const [activeTab, setActiveTab] = useState("oneTime") // 'oneTime', 'recurring'
	const [groupBy, setGroupBy] = useState("status") // 'status', 'none'
	const [sortConfig, setSortConfig] = useState({
		key: "dueDate",
		direction: "ascending"
	})

	const tasksById = useMemo(() => {
		return tasks.reduce((acc, task) => {
			acc[task.task_id] = task
			return acc
		}, {})
	}, [tasks])

	const handleSort = (key) => {
		setSortConfig((prevConfig) => {
			if (prevConfig.key === key) {
				// Flip direction if same key is clicked
				return {
					...prevConfig,
					direction:
						prevConfig.direction === "ascending"
							? "descending"
							: "ascending"
				}
			}
			// Otherwise, set new key with default ascending direction
			return { key, direction: "ascending" }
		})
	}

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

		return grouped
	}, [tasks, activeTab, groupBy, sortConfig])

	const isRecurring = activeTab === "recurring"
	const gridCols = isRecurring
		? "grid-cols-[minmax(0,_1fr)_120px_120px_150px]"
		: "grid-cols-[minmax(0,_1fr)_120px_120px_120px_150px]" // No change needed here

	return (
		<div className="w-full max-w-6xl mx-auto">
			<div className="flex items-center justify-end gap-4 p-2 mb-2">
				<div className="flex items-center gap-4">
					<div>
						<label className="text-xs text-neutral-400 mr-2">
							Show:
						</label>
						<select
							value={activeTab}
							onChange={(e) => setActiveTab(e.target.value)}
							className="bg-dark-surface p-1 rounded text-sm"
						>
							<option value="oneTime">One-time</option>
							<option value="recurring">Recurring</option>
						</select>
					</div>
					<div>
						<label className="text-xs text-neutral-400 mr-2">
							Group by:
						</label>
						<select
							value={groupBy}
							onChange={(e) => setGroupBy(e.target.value)}
							className="bg-dark-surface p-1 rounded text-sm"
						>
							<option value="status">Status</option>
							<option value="none">None</option>
						</select>
					</div>
				</div>
			</div>

			{/* Conditionally render the new QuickAddTask component */}
			{activeTab === "oneTime" && (
				<QuickAddTask onTaskAdded={onTaskAdded} />
			)}

			<div className="bg-dark-surface/50 border border-dark-surface-elevated rounded-lg overflow-hidden">
				<div className="overflow-x-auto custom-scrollbar">
					<div className="min-w-[700px]">
						<div
							className={cn(
								"hidden md:grid items-center p-2 border-b border-dark-surface-elevated text-xs uppercase",
								gridCols
							)}
						>
							<div className="px-2">Name</div>
							<SortableHeader
								title="Assignee"
								sortKey="assignee"
								sortConfig={sortConfig}
								onSort={handleSort}
							/>
							{!isRecurring && (
								<SortableHeader
									title="Due Date"
									sortKey="dueDate"
									sortConfig={sortConfig}
									onSort={handleSort}
								/>
							)}
							<SortableHeader
								title="Priority"
								sortKey="priority"
								sortConfig={sortConfig}
								onSort={handleSort}
							/>
							<div className="text-center font-bold text-neutral-400">
								Status
							</div>
						</div>

						{Object.keys(processedTasks).length > 0 ? (
							<AnimatePresence>
								{Object.entries(processedTasks).map(
									([groupName, groupTasks]) => (
										<motion.div key={groupName} layout>
											{groupBy !== "none" &&
												groupTasks.length > 0 && (
													<div className="p-2 bg-dark-surface-elevated">
														<h3 className="font-semibold text-sm text-neutral-300">
															{groupName} (
															{groupTasks.length})
														</h3>
													</div>
												)}
											{groupTasks.length > 0 &&
												groupTasks.map((task) => {
													const originalTask =
														task.source_event_id
															? tasksById[
																	task
																		.source_event_id
																]
															: null
													return (
														<TaskListItem
															key={task.task_id}
															task={task}
															onViewDetails={
																onViewDetails
															}
															onEditTask={
																onEditTask
															}
															onDeleteTask={
																onDeleteTask
															}
															onRerunTask={
																onRerunTask
															}
															onMarkComplete={
																onMarkComplete
															}
															onAssigneeChange={
																onAssigneeChange
															}
															originalTask={
																originalTask
															}
															activeTab={
																activeTab
															}
														/>
													)
												})}
										</motion.div>
									)
								)}
							</AnimatePresence>
						) : (
							<div className="text-center p-10 text-neutral-500">
								No {isRecurring ? "recurring" : "one-time"}{" "}
								tasks found.
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	)
}

export default AllTasksView
