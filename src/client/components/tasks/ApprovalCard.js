"use client"

import React from "react"
import { motion } from "framer-motion"
import {
	IconCircleCheck,
	IconPencil,
	IconTrash,
	IconAlertTriangle,
	IconChevronRight
} from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"

const ApprovalCard = ({
	task,
	integrations = [],
	onApproveTask,
	onDeleteTask,
	onEditTask,
	onViewDetails
}) => {
	let missingTools = []
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

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, x: -20 }}
			className="bg-dark-surface/70 p-3 rounded-lg border border-dark-surface-elevated hover:border-sentient-blue/50 transition-colors"
		>
			<div onClick={() => onViewDetails(task)} className="cursor-pointer">
				<p className="font-medium text-sm text-white mb-2">
					{task.name}
				</p>

				{/* Simplified Plan Visualization */}
				{task.plan && task.plan.length > 0 && (
					<div className="flex items-center gap-1 my-2">
						{task.plan.map((step, index) => (
							<React.Fragment key={index}>
								<div
									className="p-1.5 bg-dark-surface-elevated rounded-full"
									data-tooltip-id="tasks-tooltip"
									data-tooltip-content={`${step.tool}: ${step.description}`}
									data-tooltip-place="top"
								>
									{/* Placeholder for tool icon */}
									<div className="h-4 w-4 bg-neutral-600 rounded-full" />
								</div>
								{index < task.plan.length - 1 && (
									<IconChevronRight
										size={14}
										className="text-neutral-500"
									/>
								)}
							</React.Fragment>
						))}
					</div>
				)}
			</div>

			<div className="flex items-center justify-end gap-2 mt-2 pt-2 border-t border-dark-surface-elevated">
				<button
					onClick={() => onDeleteTask(task.task_id)}
					className="p-2 rounded-md text-neutral-400 hover:bg-red-500/20 hover:text-red-400 transition-colors"
				>
					<IconTrash size={16} />
				</button>
				<button
					onClick={() => onEditTask(task)}
					className="p-2 rounded-md text-neutral-400 hover:bg-orange-500/20 hover:text-orange-400 transition-colors"
				>
					<IconPencil size={16} />
				</button>
				<button
					onClick={() => onApproveTask(task.task_id)}
					disabled={missingTools.length > 0}
					className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold bg-green-500/10 text-green-300 hover:bg-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
				>
					<IconCircleCheck size={14} /> Approve
				</button>
			</div>
		</motion.div>
	)
}

export default ApprovalCard
