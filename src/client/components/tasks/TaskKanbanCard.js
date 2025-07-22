"use client"

import React from "react"
import { useDrag } from "react-dnd"
import { motion } from "framer-motion"
import toast from "react-hot-toast"
import { cn } from "@utils/cn"
import { IconPencil, IconTrash, IconRepeat } from "@tabler/icons-react"
import { taskStatusColors, priorityMap } from "./constants"

const TaskKanbanCard = ({ task, onViewDetails, onEditTask, onDataChange }) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default
	const isRecurring = task.schedule?.type === "recurring"

	const [{ isDragging }, drag] = useDrag(() => ({
		type: "task",
		item: { ...task, type: "task" },
		canDrag: !isRecurring,
		collect: (monitor) => ({ isDragging: !!monitor.isDragging() })
	}))

	const handleAction = async (actionFn, successMessage, ...args) => {
		const toastId = toast.loading("Processing...")
		try {
			const response = await actionFn(...args)
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "Action failed")
			}
			toast.success(successMessage, { id: toastId })
			if (onDataChange) onDataChange()
		} catch (error) {
			toast.error(`Error: ${error.message}`, { id: toastId })
		}
	}

	const deleteTask = (taskId) =>
		fetch("/api/tasks/delete", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ taskId })
		})

	const duplicateTask = (taskId) =>
		fetch("/api/tasks/rerun", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ taskId })
		})

	const handleDelete = (e) => {
		e.stopPropagation()
		if (window.confirm("Are you sure you want to delete this task?")) {
			handleAction(deleteTask, "Task deleted.", task.task_id)
		}
	}

	const handleDuplicate = (e) => {
		e.stopPropagation()
		handleAction(duplicateTask, "Task duplicated for re-run.", task.task_id)
	}

	return (
		<motion.div
			ref={drag}
			layout
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			whileHover={{
				scale: 1.03,
				boxShadow: "0 4px 15px rgba(0,0,0,0.2)"
			}}
			onClick={() => onViewDetails(task)}
			className={cn(
				"bg-dark-surface p-3 rounded-lg border-l-4 cursor-pointer group relative transition-all duration-200",
				isDragging && "opacity-50 scale-105",
				!isRecurring && "hover:bg-dark-surface-elevated",
				isRecurring
					? `border-dashed ${statusInfo.border} cursor-default`
					: `${statusInfo.border}`
			)}
		>
			<p className="text-sm font-medium leading-relaxed text-neutral-100">
				{task.description}
			</p>
			<div className="flex items-center justify-between mt-3 pt-2 border-t border-white/5 min-h-[28px]">
				<div className="flex items-center gap-2 text-xs text-neutral-400">
					<div
						className={cn(
							"w-2 h-2 rounded-full",
							priorityInfo.color.replace("text-", "bg-")
						)}
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content={`Priority: ${priorityInfo.label}`}
					/>
					{isRecurring && <IconRepeat size={14} />}
					<span>
						{task.schedule.run_at
							? new Date(task.schedule.run_at).toLocaleTimeString(
									[],
									{ hour: "2-digit", minute: "2-digit" }
								)
							: "Any time"}
					</span>
				</div>
				<div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
					<motion.button
						onClick={handleDuplicate}
						className="p-1.5 rounded-md text-neutral-400 hover:text-white hover:bg-dark-surface-elevated transition-all"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Duplicate Task"
					>
						<IconRepeat size={14} />
					</motion.button>
					{!isRecurring && (
						<motion.button
							onClick={(e) => {
								e.stopPropagation()
								onEditTask(task)
							}}
							className="p-1.5 rounded-md text-neutral-400 hover:text-white hover:bg-dark-surface-elevated transition-all"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Edit"
						>
							<IconPencil size={14} />
						</motion.button>
					)}
					<motion.button
						onClick={handleDelete}
						className="p-1.5 rounded-md text-neutral-400 hover:text-red-400 hover:bg-red-400/10 transition-all"
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
