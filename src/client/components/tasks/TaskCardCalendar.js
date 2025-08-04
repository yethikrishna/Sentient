"use client"
import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { taskStatusColors } from "./constants"
import { getDisplayName } from "@utils/taskUtils"

const TaskCardCalendar = ({ task, onSelectTask }) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	return (
		<motion.div
			layout
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={(e) => {
				e.stopPropagation()
				onSelectTask(task)
			}}
			className={cn(
				"w-full p-2 rounded-md text-xs font-medium text-white cursor-pointer truncate",
				"bg-brand-gray/20 hover:bg-brand-gray/80"
			)}
		>
			<div className="flex items-center gap-2">
				<div
					className={cn(
						"w-2 h-2 rounded-full flex-shrink-0",
						statusInfo.bgColor
					)}
				/>
				<span className="truncate">{getDisplayName(task)}</span>
			</div>
		</motion.div>
	)
}

export default TaskCardCalendar
