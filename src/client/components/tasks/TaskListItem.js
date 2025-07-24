import React, { useMemo } from "react"
import { motion } from "framer-motion"
import { format } from "date-fns"
import {
	IconCircleCheck,
	IconCircleHalf2,
	IconCircleDashed,
	IconCircleCheckFilled,
	IconHourglass,
	IconSparkles
} from "@tabler/icons-react"
import { cn } from "@/utils/cn"

const taskStatusColors = {
	pending: {
		label: "Pending",
		icon: IconCircleDashed,
		color: "text-blue-400"
	},
	"in-progress": {
		label: "In Progress",
		icon: IconCircleHalf2,
		color: "text-yellow-400"
	},
	completed: {
		label: "Completed",
		icon: IconCircleCheckFilled,
		color: "text-green-400"
	},
	overdue: {
		label: "Overdue",
		icon: IconHourglass,
		color: "text-red-400"
	},
	default: {
		label: "Unknown",
		icon: IconCircleDashed,
		color: "text-neutral-400"
	}
}

const priorityMap = {
	low: { label: "Low", color: "text-green-400" },
	medium: { label: "Medium", color: "text-yellow-400" },
	high: { label: "High", color: "text-red-400" },
	default: { label: "N/A", color: "text-neutral-400" }
}

export const TaskListItem = ({ task, onViewDetails, activeTab }) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	const assigneeDisplay = useMemo(() => {
		return (
			<div
				className="flex items-center gap-1.5 text-neutral-400"
				data-tooltip-id="tasks-tooltip"
				data-tooltip-content="Assigned to AI"
			>
				<IconSparkles size={14} className="text-sentient-blue" />
				<span>Sentient</span>
			</div>
		)
	}, [task])

	const dueDate =
		task.schedule?.run_at && activeTab !== "recurring"
			? format(new Date(task.schedule.run_at), "MMM dd, yyyy")
			: "N/A"

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
				<div className="md:hidden flex-shrink-0">
					<statusInfo.icon
						className={cn("h-5 w-5", statusInfo.color)}
					/>
				</div>
			</div>
			<div className="md:hidden flex items-center justify-between text-xs text-neutral-400 mt-2">
				<div className="flex items-center gap-3">
					{assigneeDisplay}
					<span className={cn("font-medium", priorityInfo.color)}>
						{priorityInfo.label}
					</span>
					{activeTab === "oneTime" && <span>{dueDate}</span>}
				</div>
			</div>

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
