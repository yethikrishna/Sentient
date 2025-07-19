"use client"

import React, { useState, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { format, parseISO } from "date-fns"
import {
	IconSparkles,
	IconUser,
	IconPencil,
	IconTrash,
	IconRepeat,
	IconArrowUp,
	IconArrowDown,
	IconSelector
} from "@tabler/icons-react"
import { taskStatusColors, priorityMap } from "./constants"
import { cn } from "@utils/cn"

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
	activeTab
}) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const assigneeIcon =
		task.assignee === "ai" ? (
			<IconSparkles
				size={18}
				className="text-blue-400"
				data-tooltip-id="tasks-tooltip"
				data-tooltip-content="Assigned to AI"
			/>
		) : (
			<IconUser
				size={18}
				className="text-gray-400"
				data-tooltip-id="tasks-tooltip"
				data-tooltip-content="Assigned to You"
			/>
		)

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
			<div className="truncate pr-4 font-medium flex items-center gap-2">
				<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
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
			<div className="flex items-center justify-center">
				{assigneeIcon}
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
	onRerunTask
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
		<div className="w-full max-w-6xl mx-auto">
			<div className="flex items-center justify-between gap-4 p-2 mb-2">
				<div className="flex items-center gap-2 p-1 bg-dark-surface rounded-lg">
					<button
						onClick={() => setActiveTab("oneTime")}
						className={cn(
							"px-3 py-1 rounded-md text-sm",
							activeTab === "oneTime" && "bg-sentient-blue"
						)}
					>
						One Time
					</button>
					<button
						onClick={() => setActiveTab("recurring")}
						className={cn(
							"px-3 py-1 rounded-md text-sm",
							activeTab === "recurring" && "bg-sentient-blue"
						)}
					>
						Recurring
					</button>
				</div>
				<div className="flex items-center gap-4">
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

			<div className="bg-dark-surface/50 border border-dark-surface-elevated rounded-lg">
				<div
					className={cn(
						"grid items-center p-2 border-b border-dark-surface-elevated text-xs uppercase",
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
										groupTasks.map((task) => (
											<TaskListItem
												key={task.task_id}
												task={task}
												onViewDetails={onViewDetails}
												onEditTask={onEditTask}
												onDeleteTask={onDeleteTask}
												onRerunTask={onRerunTask}
												activeTab={activeTab}
											/>
										))}
								</motion.div>
							)
						)}
					</AnimatePresence>
				) : (
					<div className="text-center p-10 text-neutral-500">
						No {isRecurring ? "recurring" : "one-time"} tasks found.
					</div>
				)}
			</div>
		</div>
	)
}

export default AllTasksView
