"use client"

import React from "react"
import {
	IconRefresh,
	IconPlayerPause,
	IconPlayerPlay,
	IconTrash
} from "@tabler/icons-react"

const WorkflowCard = ({ task, onToggleEnable, onDeleteTask }) => {
	const schedule = task.schedule || {}
	let scheduleText = "Recurring"
	if (schedule.frequency === "daily") {
		scheduleText = `Daily at ${schedule.time || "N/A"}`
	} else if (schedule.frequency === "weekly") {
		scheduleText = `Weekly on ${schedule.days?.join(", ") || "N/A"} at ${
			schedule.time || "N/A"
		}`
	}

	return (
		<div className="group flex items-center gap-4 bg-dark-surface/50 p-3 rounded-lg border border-transparent hover:bg-dark-surface">
			<div className="flex-grow">
				<p className="font-medium text-white text-sm">
					{task.description}
				</p>
				<p className="text-xs text-neutral-400 flex items-center gap-1 mt-1">
					<IconRefresh size={12} />
					{scheduleText}
				</p>
			</div>
			<div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
				<button
					onClick={() => onToggleEnable(task.task_id, task.enabled)}
					className={`p-1.5 rounded-md ${task.enabled ? "text-orange-400" : "text-green-400"} hover:bg-dark-surface-elevated`}
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content={task.enabled ? "Pause" : "Resume"}
				>
					{task.enabled ? (
						<IconPlayerPause size={16} />
					) : (
						<IconPlayerPlay size={16} />
					)}
				</button>
				<button
					onClick={() => onDeleteTask(task.task_id)}
					className="p-1.5 rounded-md text-neutral-400 hover:bg-red-500/20 hover:text-red-400"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Delete"
				>
					<IconTrash size={16} />
				</button>
			</div>
		</div>
	)
}

export default WorkflowCard
