"use client"

import React, { useState, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { format, parseISO } from "date-fns"
import {
	IconSparkles,
	IconUser,
	IconPencil,
	IconTrash,
	IconRepeat
} from "@tabler/icons-react"
import { taskStatusColors, priorityMap } from "./constants"
import { cn } from "@utils/cn"

// New Task List Item component
const TaskListItem = ({
	task,
	onViewDetails,
	onEditTask,
	onDeleteTask,
	onRerunTask
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

	const dueDate = task.schedule?.run_at
		? format(parseISO(task.schedule.run_at), "MMM d")
		: "No date"

	const gridTemplateColumns = "minmax(0, 1fr) 120px 120px 150px"

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
			<div className="text-center text-neutral-400">{dueDate}</div>
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
	const [groupBy, setGroupBy] = useState("status") // 'status', 'priority', 'none'
	const [sortBy, setSortBy] = useState("dueDate") // 'dueDate', 'priority'

	const processedTasks = useMemo(() => {
		let sortedTasks = [...tasks]
		// Sort logic
		sortedTasks.sort((a, b) => {
			// Primary sort
			let compareA, compareB
			if (sortBy === "dueDate") {
				compareA = a.schedule?.run_at
					? parseISO(a.schedule.run_at).getTime()
					: Infinity
				compareB = b.schedule?.run_at
					? parseISO(b.schedule.run_at).getTime()
					: Infinity
			} else {
				// sortBy 'priority'
				compareA = a.priority ?? 2
				compareB = b.priority ?? 2
			}

			if (compareA < compareB) return -1
			if (compareA > compareB) return 1

			// Secondary sort
			const secondarySortBy =
				sortBy === "priority" ? "dueDate" : "priority"
			if (secondarySortBy === "priority") {
				const priorityA = a.priority ?? 2
				const priorityB = b.priority ?? 2
				return priorityA - priorityB
			} else {
				const dateA = a.schedule?.run_at
					? parseISO(a.schedule.run_at).getTime()
					: Infinity
				const dateB = b.schedule?.run_at
					? parseISO(b.schedule.run_at).getTime()
					: Infinity
				return dateA - dateB
			}
		})

		// Group logic
		if (groupBy === "none") {
			return { "All Tasks": sortedTasks }
		}

		const grouped = sortedTasks.reduce((acc, task) => {
			let key
			if (groupBy === "status") {
				key = taskStatusColors[task.status]?.label || "Unknown"
			} else {
				// groupBy 'priority'
				key = priorityMap[task.priority]?.label || "Medium"
			}
			if (!acc[key]) {
				acc[key] = []
			}
			acc[key].push(task)
			return acc
		}, {})

		return grouped
	}, [tasks, groupBy, sortBy])

	return (
		<div className="w-full max-w-6xl mx-auto">
			<div className="flex items-center justify-end gap-4 p-2 mb-2">
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
						<option value="priority">Priority</option>
						<option value="none">None</option>
					</select>
				</div>
				<div>
					<label className="text-xs text-neutral-400 mr-2">
						Sort by:
					</label>
					<select
						value={sortBy}
						onChange={(e) => setSortBy(e.target.value)}
						className="bg-dark-surface p-1 rounded text-sm"
					>
						<option value="dueDate">Due Date</option>
						<option value="priority">Priority</option>
					</select>
				</div>
			</div>

			<div className="bg-dark-surface/50 border border-dark-surface-elevated rounded-lg">
				<div className="grid grid-cols-[minmax(0,_1fr)_120px_120px_150px] items-center p-2 border-b border-dark-surface-elevated text-xs text-neutral-400 font-bold uppercase">
					<div className="px-2">Name</div>
					<div className="text-center">Assignee</div>
					<div className="text-center">Due date</div>
					<div className="text-center">Status</div>
				</div>

				<AnimatePresence>
					{Object.entries(processedTasks).map(
						([groupName, groupTasks]) => (
							<motion.div key={groupName} layout>
								{groupBy !== "none" && (
									<div className="p-2 bg-dark-surface-elevated">
										<h3 className="font-semibold text-neutral-300">
											{groupName} ({groupTasks.length})
										</h3>
									</div>
								)}
								{groupTasks.map((task) => (
									<TaskListItem
										key={task.task_id}
										task={task}
										onViewDetails={onViewDetails}
										onEditTask={onEditTask}
										onDeleteTask={onDeleteTask}
										onRerunTask={onRerunTask}
									/>
								))}
							</motion.div>
						)
					)}
				</AnimatePresence>
			</div>
		</div>
	)
}

export default AllTasksView
