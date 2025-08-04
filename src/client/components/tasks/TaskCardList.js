"use client"
import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { taskStatusColors, priorityMap } from "./constants"
import { format } from "date-fns"
import { BorderTrail } from "@components/ui/border-trail"

const StatusBadge = ({ status }) => {
	const statusInfo = taskStatusColors[status] || taskStatusColors.default

	return (
		<div
			className={cn(
				"px-2 py-0.5 rounded-full text-xs font-medium flex items-center gap-1.5",
				statusInfo.bgColor,
				statusInfo.textColor
			)}
		>
			<statusInfo.icon size={12} />
			{statusInfo.label}
		</div>
	)
}

const TaskCardList = ({ task, onSelectTask }) => {
	let dateText = ""
	if (task.scheduled_date) {
		try {
			const date = task.scheduled_date
			dateText = format(date, "MMM d")
		} catch (e) {
			// ignore invalid date
		}
	}

	const inProgress = [
		"processing",
		"planning",
		"clarification_answered"
	].includes(task.status)

	const getDisplayName = (task) => {
		// Use description if name is generic
		if (task.name === "Proactively generated plan" && task.description) {
			return task.description
		}
		// Fallback to the original prompt if description is also generic/missing
		if (
			task.name === "Proactively generated plan" &&
			task.runs &&
			task.runs.length > 0 &&
			task.runs[0].prompt
		) {
			return task.runs[0].prompt
		}
		return task.name || "Untitled Task"
	}

	const cardVariants = {
		hidden: { opacity: 0, y: -20, scale: 0.95 },
		visible: { opacity: 1, y: 0, scale: 1 }
	}

	return (
		<motion.div
			layout
			variants={cardVariants}
			exit={{ opacity: 0, transition: { duration: 0.1 } }}
			onClick={() => onSelectTask(task)}
			className="bg-neutral-900/50 p-4 rounded-lg border border-zinc-700 hover:border-brand-orange transition-all cursor-pointer relative"
		>
			{inProgress && (
				<BorderTrail size={80} className="bg-brand-yellow" />
			)}
			<div className="flex bg-transparent p-1 transition-all justify-between items-start gap-4">
				<p className="font-sans font-semibold text-brand-white flex-1 text-sm line-clamp-2">
					{getDisplayName(task)}
				</p>
				<StatusBadge status={task.status} />
			</div>
			<div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-800 text-xs text-neutral-400 font-mono">
				{dateText && <span>{dateText}</span>}
			</div>
		</motion.div>
	)
}

export default TaskCardList
