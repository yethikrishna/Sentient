"use client"

import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { taskStatusColors } from "./constants"

const TaskSearchResultCard = ({ task, onSelect }) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default

	return (
		<motion.div
			layout
			initial={{ opacity: 0, x: -10 }}
			animate={{ opacity: 1, x: 0 }}
			whileHover={{
				y: -3,
				scale: 1.02,
				boxShadow:
					"0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
			}}
			onClick={() => onSelect(task)}
			className={cn(
				"bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-3 rounded-lg border cursor-pointer backdrop-blur-sm shadow-sm group",
				statusInfo
					? `border-l-4 ${statusInfo.border}`
					: "border-transparent"
			)}
		>
			<div className="flex items-center gap-3">
				<div className="flex-shrink-0">
					<statusInfo.icon
						className={cn("h-5 w-5", statusInfo.color)}
					/>
				</div>
				<div className="flex-grow min-w-0">
					<p
						className="font-medium text-white text-sm truncate"
						title={task.name}
					>
						{task.name}
					</p>
					<p className="text-xs text-gray-400 capitalize">
						Task: {task.status.replace("_", " ")}
					</p>
				</div>
			</div>
		</motion.div>
	)
}

export default TaskSearchResultCard
