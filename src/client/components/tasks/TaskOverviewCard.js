"use client"

import React from "react"
import { cn } from "@utils/cn"
import { taskStatusColors, priorityMap } from "./constants"
import { IconPencil, IconTrash, IconRepeat } from "@tabler/icons-react"

const TaskOverviewCard = ({
	task,
	onViewDetails,
	onEditTask,
	onDeleteTask,
	onRerunTask
}) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default
	const scheduleText = task.schedule?.run_at
		? new Date(task.schedule.run_at).toLocaleDateString()
		: "Unscheduled"

	return (
		<div
			onClick={(e) => {
				if (e.target.closest("button") || !onViewDetails) return
				onViewDetails(task)
			}}
			className={cn(
				"group flex items-center gap-4 bg-dark-surface/50 p-3 rounded-lg border border-transparent",
				"hover:bg-dark-surface",
				"cursor-pointer"
			)}
		>
			<div className="flex-grow min-w-0 font-medium text-white text-sm">
				{task.description}
			</div>
			<div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
				<button
					onClick={(e) => {
						e.stopPropagation()
						onRerunTask(task.task_id)
					}}
					className="p-1.5 rounded-md text-neutral-400 hover:bg-dark-surface-elevated"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Rerun Task"
				>
					<IconRepeat size={16} />
				</button>
				<button
					onClick={(e) => {
						e.stopPropagation()
						onEditTask(task)
					}}
					className="p-1.5 rounded-md text-neutral-400 hover:bg-dark-surface-elevated"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Edit"
				>
					<IconPencil size={16} />
				</button>
				<button
					onClick={(e) => {
						e.stopPropagation()
						onDeleteTask(task.task_id)
					}}
					className="p-1.5 rounded-md text-neutral-400 hover:bg-red-500/20 hover:text-red-400"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Delete"
				>
					<IconTrash size={16} />
				</button>
			</div>
			<div className="w-24 text-center text-xs font-semibold">
				<span className={priorityInfo.color}>{priorityInfo.label}</span>
			</div>
			<div className="w-24 text-center text-xs text-neutral-400">
				{scheduleText}
			</div>
			<div className="w-32 flex items-center justify-center gap-2 text-xs">
				<statusInfo.icon className={cn("h-4 w-4", statusInfo.color)} />
				<span className={statusInfo.color}>{statusInfo.label}</span>
			</div>
		</div>
	)
}

export default TaskOverviewCard
