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
		<div className="group flex flex-col gap-2 bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-2.5 rounded-lg shadow-sm border border-transparent hover:border-blue-500/30">
			<p
				className="font-medium text-white text-sm truncate"
				title={task.description}
			>
				{task.description}
			</p>
			<div className="flex items-center justify-between">
				<p className="text-xs text-neutral-400 flex items-center gap-1">
					<IconRefresh size={12} />
					{scheduleText}
				</p>
				<div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
					<button
						onClick={() =>
							onToggleEnable(task.task_id, task.enabled)
						}
						className={`p-1.5 rounded-md ${task.enabled ? "text-orange-400" : "text-green-400"} hover:bg-neutral-700`}
						data-tooltip-id="organizer-tooltip"
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
						className="p-1.5 rounded-md text-red-400 hover:bg-red-400/20"
						data-tooltip-id="organizer-tooltip"
						data-tooltip-content="Delete"
					>
						<IconTrash size={16} />
					</button>
				</div>
			</div>
		</div>
	)
}

export default WorkflowCard
