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

	const cardContent = (
		<motion.div
			layout
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={() => onSelectTask(task)}
			className="bg-brand-black p-4 rounded-lg border border-zinc-700 hover:border-brand-orange transition-all cursor-pointer relative"
		>
			<div className="flex justify-between items-start gap-4">
				<p className="font-sans font-semibold text-brand-white flex-1 text-sm">
					{task.description}
				</p>
				<StatusBadge status={task.status} />
			</div>
			<div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-800 text-xs text-neutral-400 font-mono">
				{dateText && <span>{dateText}</span>}
			</div>
		</motion.div>
	)

	return inProgress ? (
		<div className="relative">
			<BorderTrail
				size={80}
				className="bg-brand-yellow"
				style={{ boxShadow: "none" }}
			/>
			{cardContent}
		</div>
	) : (
		cardContent
	)
}

export default TaskCardList
