"use client"

import React from "react"
import { useDrop } from "react-dnd"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { isToday, format } from "date-fns"
import TaskKanbanCard from "./TaskKanbanCard"

const DayColumn = ({
	date,
	tasks,
	recurringTasks,
	onTaskDrop,
	...handlers
}) => {
	const dayLabel = format(date, "EEE")

	const [{ isOver }, drop] = useDrop(() => ({
		accept: "task",
		drop: (item) => onTaskDrop(item, date),
		collect: (monitor) => ({
			isOver: !!monitor.isOver()
		})
	}))

	return (
		<motion.div
			ref={drop}
			className={cn(
				"flex flex-col bg-dark-surface/50 rounded-xl h-full transition-colors min-w-[300px] flex-shrink-0",
				isOver && "bg-dark-surface"
			)}
		>
			<div className="flex items-center gap-3 p-4 border-b border-white/5">
				<h3 className="font-semibold text-lg">
					<span className={cn(isToday(date) && "text-sentient-blue")}>
						{dayLabel}
					</span>
				</h3>
				<span className="text-sm font-medium text-neutral-500">
					{format(date, "d MMM")}
				</span>
			</div>
			<div className="p-3 space-y-2.5 flex-1 overflow-y-auto custom-scrollbar">
				{recurringTasks.map((task) => (
					<TaskKanbanCard
						key={`recur-${task.task_id}`}
						task={task}
						{...handlers}
					/>
				))}
				{tasks.map((task) => (
					<TaskKanbanCard
						key={task.task_id}
						task={task}
						{...handlers}
					/>
				))}
				{tasks.length === 0 && recurringTasks.length === 0 && (
					<div className="text-center py-10 text-sm text-[var(--color-text-muted)]">
						No tasks for this day.
					</div>
				)}
			</div>
		</motion.div>
	)
}

export default DayColumn
