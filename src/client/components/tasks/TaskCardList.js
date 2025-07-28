"use client"
import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { taskStatusColors, priorityMap } from "./constants"
import { format } from "date-fns"

const TaskCardList = ({ task, onSelectTask }) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	let dateText = ""
	if (task.scheduled_date) {
		try {
			const date = task.scheduled_date
			dateText = format(date, "MMM d")
		} catch (e) {
			// ignore invalid date
		}
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={() => onSelectTask(task)}
			className="bg-neutral-800/50 p-4 rounded-lg border border-neutral-700 hover:border-sentient-blue transition-colors cursor-pointer"
		>
			<div className="flex justify-between items-start gap-4">
				<p className="font-medium text-white flex-1">
					{task.description}
				</p>
				<div className="flex items-center gap-2 text-xs flex-shrink-0">
					<statusInfo.icon
						className={cn("h-4 w-4", statusInfo.color)}
					/>
					<span className={cn("font-semibold", statusInfo.color)}>
						{statusInfo.label}
					</span>
				</div>
			</div>
			<div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-800 text-xs text-neutral-400">
				<span className={cn("font-semibold", priorityInfo.color)}>
					{priorityInfo.label} Priority
				</span>
				{dateText && <span>{dateText}</span>}
			</div>
		</motion.div>
	)
}

export default TaskCardList
