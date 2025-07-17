"use client"

import React, { useMemo } from "react"
import { useDrop } from "react-dnd"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { isToday, isSameDay, subDays, addDays, format } from "date-fns"
import TaskKanbanCard from "./TaskKanbanCard"

const DayColumn = ({
	date,
	tasks,
	onViewTask,
	onEditTask,
	onDeleteTask,
	onDuplicateTask,
	onTaskDrop
}) => {
	const isCurrentDay = isToday(date)
	const isYesterday = isSameDay(date, subDays(new Date(), 1))
	const isTomorrow = isSameDay(date, addDays(new Date(), 1))

	const dayLabel = useMemo(() => {
		if (isCurrentDay) return "Today"
		if (isYesterday) return "Yesterday"
		if (isTomorrow) return "Tomorrow"
		return format(date, "eee")
	}, [date, isCurrentDay, isYesterday, isTomorrow])

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
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			transition={{ duration: 0.4, ease: "easeOut" }}
			className={cn("flex flex-col bg-[var(--color-primary-surface)]/20 rounded-2xl h-full transition-colors",
			isOver && "bg-[var(--color-primary-surface)]/60")}
		>
			<div className="flex justify-between items-center p-4 border-b border-[var(--color-primary-surface)]/50">
				<h3 className="font-semibold text-lg flex items-center gap-2">
					<span
						className={cn(
							isCurrentDay && "text-[var(--color-accent-blue)]"
						)}
					>
						{dayLabel}
					</span>
					<span
						className={cn(
							"text-lg font-bold text-neutral-400",
							isCurrentDay && "text-white"
						)}
					>
						{format(date, "d MMM")}
					</span>
				</h3>
			</div>
			<div className="p-3 space-y-3 flex-1 overflow-y-auto custom-scrollbar">
				{tasks.map((task) => (
					<TaskKanbanCard
						key={task.task_id}
						task={task}
						onViewTask={onViewTask}
						onEditTask={onEditTask}
						onDeleteTask={onDeleteTask}
						onDuplicateTask={onDuplicateTask}
					/>
				))}
				{tasks.length === 0 && (
					<div className="text-center py-10 text-sm text-[var(--color-text-muted)]">
						No tasks for this day.
					</div>
				)}
			</div>
		</motion.div>
	)
}

export default DayColumn
