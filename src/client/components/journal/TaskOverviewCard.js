"use client"

import React from "react"
import { motion } from "framer-motion"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"
import { taskStatusColors } from "./constants"
import {
	IconAlertTriangle,
	IconCircleCheck,
	IconPencil,
	IconTrash
} from "@tabler/icons-react"

const TaskOverviewCard = ({
	task,
	onEditTask,
	onDeleteTask,
	onApproveTask,
	integrations,
	onViewDetails
}) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	let missingTools = []
	if (task.status === "approval_pending" && integrations) {
		const requiredTools = new Set(task.plan?.map((step) => step.tool) || [])
		requiredTools.forEach((toolName) => {
			const integration = integrations.find((i) => i.name === toolName)
			if (
				integration &&
				!integration.connected &&
				integration.auth_type !== "builtin"
			) {
				missingTools.push(integration.display_name || toolName)
			}
		})
	}
	return (
		<motion.div
			layout
			onClick={(e) => {
				if (e.target.closest("button")) return
				onViewDetails(task)
			}}
			className={cn(
				"group flex items-center gap-3 bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-2.5 rounded-lg shadow-sm border border-transparent",
				"hover:border-blue-500/30",
				"cursor-pointer"
			)}
		>
			<div className="flex-shrink-0">
				<statusInfo.icon className={cn("h-5 w-5", statusInfo.color)} />
			</div>
			<div className="flex-grow min-w-0">
				<p
					className="font-medium text-white text-sm truncate"
					title={task.description}
				>
					{task.description}
				</p>
				{missingTools.length > 0 && (
					<div
						className="flex items-center gap-1 mt-1 text-yellow-400 text-xs"
						data-tooltip-id={`missing-tools-tooltip-sidebar-${task.task_id}`}
					>
						<IconAlertTriangle size={12} />
						<span>Requires: {missingTools.join(", ")}</span>
						<Tooltip
							id={`missing-tools-tooltip-sidebar-${task.task_id}`}
							content="Please connect these tools in Settings to approve this task."
							place="left"
						/>
					</div>
				)}
			</div>
			<div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
				{task.status === "approval_pending" && (
					<>
						<button
							onClick={() => onApproveTask(task.task_id)}
							className="p-1.5 rounded-md text-green-400 hover:bg-green-400/20 disabled:text-gray-600 disabled:cursor-not-allowed"
							data-tooltip-id="journal-tooltip"
							data-tooltip-content="Approve"
							disabled={missingTools.length > 0}
						>
							<IconCircleCheck size={16} />
						</button>
						<button
							onClick={() => onEditTask(task)}
							className="p-1.5 rounded-md text-orange-400 hover:bg-orange-400/20"
							data-tooltip-id="journal-tooltip"
							data-tooltip-content="Edit"
						>
							<IconPencil size={16} />
						</button>
					</>
				)}
				<button
					onClick={() => onDeleteTask(task.task_id)}
					className="p-1.5 rounded-md text-red-400 hover:bg-red-400/20"
					data-tooltip-id="journal-tooltip"
					data-tooltip-content="Delete"
				>
					<IconTrash size={16} />
				</button>
			</div>
		</motion.div>
	)
}

export default TaskOverviewCard
