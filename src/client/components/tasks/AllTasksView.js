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
		<div className="flex items-center gap-3 p-3 mb-4 bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-lg focus-within:border-[var(--color-accent-blue)] transition-colors">
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
				className="flex-1 bg-transparent text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] resize-none outline-none font-Inter"
				rows={1}
				disabled={isAdding}
			/>
			<div className="flex items-center gap-2">
				<button
					onClick={() =>
						setAssignee(assignee === "user" ? "ai" : "user")
					}
					className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-primary-surface-elevated)] rounded-md transition-colors"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content={`Assign to: ${
						assignee === "ai" ? "AI" : "Me"
					}`}
				>
					{assignee === "ai" ? (
						<IconSparkles size={16} className="text-[var(--color-accent-blue)]" />
					) : (
						<IconUser size={16} />
					)}
				</button>
				<button
					onClick={handleAddTask}
					disabled={isAdding || !prompt.trim()}
					className="p-2 bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white rounded-md disabled:opacity-50 transition-colors"
				>
					{isAdding ? (
						<IconLoader size={16} className="animate-spin" />
					) : (
						<IconPlus size={16} />
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
				"flex items-center justify-center gap-1 text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors",
				className
			)}
		>
			<span>{title}</span>
			<IconComponent
				size={14}
				className={cn(iconClassName, "transition-colors")}
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
					className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-blue)] hover:bg-[var(--color-primary-surface-elevated)] rounded transition-colors"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Assign to AI"
				>
					<IconUser size={16} />
				</button>
			)
		}
		if (task.assignee === "ai") {
			return (
				<div className="p-2">
					<IconSparkles
						size={16}
						className="text-[var(--color-accent-blue)]"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Assigned to AI"
					/>
				</div>
			)
		}
		return (
			<div className="p-2">
				<IconSparkles size={16} className="text-[var(--color-text-muted)]" />
			</div>
		)
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
			className="grid items-center p-3 border-b border-[var(--color-primary-surface)] hover:bg-[var(--color-primary-surface)] cursor-pointer text-sm group transition-colors"
			style={{ gridTemplateColumns }}
		>
			<div className="truncate pr-4 font-medium flex items-center gap-2">
				<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
					{task.assignee === "user" && task.status === "pending" && (
						<button
							onClick={(e) => {
								e.stopPropagation()
								onMarkComplete(task.task_id)
							}}
							className="p-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-accent-green)] hover:bg-[var(--color-primary-surface-elevated)] rounded transition-colors"
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
						className="p-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-accent-blue)] hover:bg-[var(--color-primary-surface-elevated)] rounded transition-colors"
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
						className="p-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-accent-orange)] hover:bg-[var(--color-primary-surface-elevated)] rounded transition-colors"
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
						className="p-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-accent-red)] hover:bg-[var(--color-primary-surface-elevated)] rounded transition-colors"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Delete"
					>
						<IconTrash size={14} />
					</button>
				</div>
				<span className="truncate">{task.description}</span>
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
		<div className="h-full flex flex-col">
			<div className="flex items-center justify-between p-6 border-b border-[var(--color-primary-surface)]">
				<div className="flex items-center gap-6">
					<div className="flex items-center gap-2">
						<label className="text-sm text-[var(--color-text-secondary)] font-medium">
							Show:
						</label>
						<select
							value={activeTab}
							onChange={(e) => setActiveTab(e.target.value)}
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
							onChange={(e) => setGroupBy(e.target.value)}
							className="bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-md px-3 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent-blue)] outline-none"
						>
							<option value="status">Status</option>
							<option value="none">None</option>
						</select>
					</div>
				</div>
			</div>

			<div className="flex-1 flex flex-col overflow-hidden">
				<div className="p-6 pb-0">
					{activeTab === "oneTime" && (
						<QuickAddTask onTaskAdded={onTaskAdded} />
					)}
				</div>

				<div className="flex-1 overflow-hidden px-6">
					<div className="h-full bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-lg overflow-hidden">
						<div className="overflow-x-auto custom-scrollbar h-full">
							<div className="min-w-[700px] h-full flex flex-col">
								<div
									className={cn(
										"hidden md:grid items-center p-3 border-b border-[var(--color-primary-surface-elevated)] text-xs uppercase font-medium text-[var(--color-text-secondary)]",
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
									<div className="text-center font-medium text-[var(--color-text-secondary)]">
										Status
									</div>
								</div>

								<div className="flex-1 overflow-y-auto">
									{Object.keys(processedTasks).length > 0 ? (
										<AnimatePresence>
											{Object.entries(processedTasks).map(
												([groupName, groupTasks]) => (
													<motion.div key={groupName} layout>
														{groupBy !== "none" &&
															groupTasks.length > 0 && (
																<div className="p-3 bg-[var(--color-primary-surface-elevated)] border-b border-[var(--color-primary-surface)]">
																	<h3 className="font-medium text-sm text-[var(--color-text-primary)]">
																		{groupName} ({groupTasks.length})
																	</h3>
																</div>
															)}
														{groupTasks.length > 0 &&
															groupTasks.map((task) => (
																<TaskListItem
																	key={task.task_id}
																	task={task}
																	onViewDetails={
																		onViewDetails
																	}
																	onEditTask={onEditTask}
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
																	activeTab={activeTab}
																/>
															))}
													</motion.div>
												)
											)}
										</AnimatePresence>
									) : (
										<div className="flex items-center justify-center h-full text-center p-8">
											<div>
												<div className="text-4xl mb-3 text-[var(--color-text-muted)]">📝</div>
												<div className="text-lg font-medium text-[var(--color-text-primary)] mb-2">
													No {isRecurring ? "recurring" : "one-time"} tasks found
												</div>
												<div className="text-sm text-[var(--color-text-secondary)]">
													{!isRecurring ? "Create your first task above!" : "Set up recurring workflows to automate your tasks."}
												</div>
											</div>
										</div>
									)}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	)
}

export default AllTasksView
