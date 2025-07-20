import React from "react"
import { motion } from "framer-motion"
import { format } from "date-fns"
import {
	IconCircleCheck,
	IconRepeat,
	IconPencil,
	IconTrash,
	IconUser,
	IconRobot,
	IconCircleHalf2,
	IconCircleDashed,
	IconCircleCheckFilled,
	IconHourglass
} from "@tabler/icons-react"
import { cn } from "@/utils/cn"

const getStatusInfo = (status) => {
	switch (status) {
		case "pending":
			return {
				label: "Pending",
				icon: IconCircleDashed,
				color: "text-blue-400"
			}
		case "in-progress":
			return {
				label: "In Progress",
				icon: IconCircleHalf2,
				color: "text-yellow-400"
			}
		case "completed":
			return {
				label: "Completed",
				icon: IconCircleCheckFilled,
				color: "text-green-400"
			}
		case "overdue":
			return {
				label: "Overdue",
				icon: IconHourglass,
				color: "text-red-400"
			}
		default:
			return {
				label: "Unknown",
				icon: IconCircleDashed,
				color: "text-neutral-400"
			}
	}
}

const getPriorityInfo = (priority) => {
	switch (priority) {
		case "low":
			return { label: "Low", color: "text-green-400" }
		case "medium":
			return { label: "Medium", color: "text-yellow-400" }
		case "high":
			return { label: "High", color: "text-red-400" }
		default:
			return { label: "N/A", color: "text-neutral-400" }
	}
}

export function TaskListItem({
	task,
	activeTab,
	onMarkComplete,
	onRerunTask,
	onEditTask,
	onDeleteTask,
	onViewDetails
}) {
	const statusInfo = getStatusInfo(task.status)
	const priorityInfo = getPriorityInfo(task.priority)

	const assigneeDisplay =
		task.assignee === "user" ? (
			<span className="flex items-center gap-1 text-neutral-400">
				<IconUser size={14} />
				You
			</span>
		) : (
			<span className="flex items-center gap-1 text-neutral-400">
				<IconRobot size={14} />
				AI
			</span>
		)

	const dueDate = task.due_date
		? format(new Date(task.due_date), "MMM dd, yyyy")
		: "N/A"

	// const gridTemplateColumns =
	// 	activeTab === "oneTime"
	// 		? "minmax(0,1fr) 120px 120px 120px 150px"
	// 		: "minmax(0,1fr) 120px 120px 150px"

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, y: -20 }}
			transition={{ duration: 0.2 }}
			onClick={() => {
				onViewDetails(task)
			}}
			className={cn(
				"p-3 md:p-2 border-b border-dark-surface-elevated hover:bg-dark-surface cursor-pointer text-sm group",
				"md:grid md:items-center",
				activeTab === "oneTime"
					? "md:grid-cols-[minmax(0,1fr)_120px_120px_120px_150px]"
					: "md:grid-cols-[minmax(0,1fr)_120px_120px_150px]"
			)}
		>
			<div className="truncate pr-4 font-medium flex items-start justify-between md:items-center md:gap-2">
				<span className="md:truncate">{task.description}</span>
				{/* Desktop-only inline actions */}
				<div className="hidden md:flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
					{task.assignee === "user" && task.status === "pending" && (
						<button
							onClick={(e) => {
								e.stopPropagation()
								onMarkComplete(task.task_id)
							}}
							className="p-1 rounded text-neutral-400 hover:bg-green-500/20 hover:text-green-400"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Mark Complete"
						>
							<IconCircleCheck size={14} />
						</button>
					)}
					<button
						onClick={(e) => {
							e.stopPropagation()
							onRerunTask(task.task_id)
						}}
						className="p-1 rounded text-neutral-400 hover:bg-dark-surface-elevated"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Rerun Task"
					>
						<IconRepeat size={14} />
					</button>
					<button
						onClick={(e) => {
							e.stopPropagation()
							onEditTask(task)
						}}
						className="p-1 rounded text-neutral-400 hover:bg-dark-surface-elevated"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Edit"
					>
						<IconPencil size={14} />
					</button>
					<button
						onClick={(e) => {
							e.stopPropagation()
							onDeleteTask(task.task_id)
						}}
						className="p-1 rounded text-neutral-400 hover:bg-red-500/20 hover:text-red-400"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Delete"
					>
						<IconTrash size={14} />
					</button>
				</div>
				{/* Mobile-only status icon */}
				<div className="md:hidden flex-shrink-0">
					<statusInfo.icon
						className={cn("h-5 w-5", statusInfo.color)}
					/>
				</div>
			</div>
			{/* Mobile meta info row */}
			<div className="md:hidden flex items-center justify-between text-xs text-neutral-400 mt-2">
				<div className="flex items-center gap-3">
					{assigneeDisplay}
					<span className={cn("font-medium", priorityInfo.color)}>
						{priorityInfo.label}
					</span>
					{activeTab === "oneTime" && <span>{dueDate}</span>}
				</div>
			</div>

			{/* Desktop-only columns */}
			<div className="hidden md:flex items-center justify-center">
				{assigneeDisplay}
			</div>
			{activeTab === "oneTime" && (
				<div className="hidden md:block text-center text-neutral-400">
					{dueDate}
				</div>
			)}
			<div
				className={cn(
					"hidden md:block text-center font-medium",
					priorityInfo.color
				)}
			>
				{priorityInfo.label}
			</div>
			<div className="hidden md:flex items-center justify-center gap-2">
				<statusInfo.icon className={cn("h-4 w-4", statusInfo.color)} />
				<span className={cn(statusInfo.color)}>{statusInfo.label}</span>
			</div>
		</motion.div>
	)
}
