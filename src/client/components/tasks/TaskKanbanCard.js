"use client"

import React from "react"
import { useDrag } from "react-dnd"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { IconPencil, IconTrash, IconRepeat } from "@tabler/icons-react"
import { taskStatusColors, priorityMap } from "./constants"

const TaskKanbanCard = ({
	task,
	onViewTask,
	onEditTask,
	onDeleteTask,
	onDuplicateTask
}) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default
	const [{ isDragging }, drag] = useDrag(() => ({
		type: "task",
		item: { id: task.task_id, schedule: task.schedule },
		collect: (monitor) => ({
			isDragging: !!monitor.isDragging(),
		}),
	}))
	return (
		<motion.div
			ref={drag}
			layout
			initial={{ opacity: 0, x: -10 }}
			animate={{ opacity: 1, x: 0 }}
			whileHover={{
				y: -3,
				scale: 1.02,
				boxShadow:
					"0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
			}}
			onClick={() => onViewTask(task)}
			className={cn(
				"bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-3 rounded-lg border cursor-pointer backdrop-blur-sm shadow-sm group",
				isDragging && "opacity-50",
				task.status || task.schedule?.type === "recurring"
					? `border-l-4 ${task.schedule?.type === "recurring" ? "border-dashed" : ""} ${statusInfo.border}`
					: "border-transparent"
			)}
		>
			<p className="text-sm leading-relaxed whitespace-pre-wrap">
				{task.description}
			</p>
			<div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5 min-h-[28px]">
				<div className="flex items-center gap-2 text-xs">
					<span
						className={cn("h-2 w-2 rounded-full", statusInfo.bg)}
					></span>
					<span className={cn("font-semibold", priorityInfo.color)}>
						{priorityInfo.label}
					</span>
				</div>
				<div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
					<motion.button
						whileHover={{ scale: 1.1, zIndex: 10 }}
						whileTap={{ scale: 0.9 }}
						onClick={(e) => {
							e.stopPropagation()
							onDuplicateTask(task.task_id)
						}}
						className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-white hover:bg-[var(--color-primary-surface)] transition-all"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Duplicate Task"
					>
						<IconRepeat size={14} />
					</motion.button>
					<motion.button
						whileHover={{ scale: 1.1, zIndex: 10 }}
						whileTap={{ scale: 0.9 }}
						onClick={(e) => {
							e.stopPropagation()
							onEditTask(task)
						}}
						className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-white hover:bg-[var(--color-primary-surface)] transition-all"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Edit"
					>
						<IconPencil size={14} />
					</motion.button>
					<motion.button
						whileHover={{ scale: 1.1, zIndex: 10 }}
						whileTap={{ scale: 0.9 }}
						onClick={(e) => {
							e.stopPropagation()
							onDeleteTask(task.task_id)
						}}
						className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-accent-red)] hover:bg-[var(--color-accent-red)]/10 transition-all"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Delete"
					>
						<IconTrash size={14} />
					</motion.button>
				</div>
			</div>
		</motion.div>
	)
}

export default TaskKanbanCard
