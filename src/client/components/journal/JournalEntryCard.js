"use client"

import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import {
	IconSparkles,
	IconRefresh,
	IconCopy,
	IconPencil,
	IconTrash
} from "@tabler/icons-react"
import { taskStatusColors } from "./constants"

const JournalEntryCard = ({
	item,
	linkedTask,
	onViewEntry,
	onEditEntry,
	onDeleteEntry,
	onDuplicateEntry
}) => {
	const taskStatus = linkedTask?.status
	const statusInfo = taskStatus
		? taskStatusColors[taskStatus] || taskStatusColors.default
		: null

	return (
		<motion.div
			layout
			initial={{ opacity: 0, x: -10 }}
			animate={{ opacity: 1, x: 0 }}
			whileHover={{
				y: -3,
				scale: 1.02,
				boxShadow:
					"0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
			}}
			onClick={() => onViewEntry(item)}
			className={cn(
				"bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-3 rounded-lg border cursor-pointer backdrop-blur-sm shadow-sm group",
				statusInfo
					? `border-l-4 ${item.isRecurring ? "border-dashed" : ""} ${statusInfo.border}`
					: "border-transparent"
			)}
		>
			<p className="text-sm leading-relaxed whitespace-pre-wrap">
				{item.content}
			</p>
			<div className="flex items-end justify-between mt-2 pt-2 border-t border-white/5 min-h-[28px]">
				<div>
					{item.isRecurring ? (
						<div className="text-xs font-semibold text-gray-400 capitalize flex items-center gap-1.5">
							<IconRefresh size={12} />
							<span>Recurring Task</span>
						</div>
					) : taskStatus ? (
						<div className="text-xs font-semibold text-gray-400 capitalize flex items-center gap-1.5">
							<IconSparkles size={12} />
							<span>Task: {taskStatus.replace("_", " ")}</span>
						</div>
					) : null}
				</div>
				{!item.isRecurring && (
					<div className="relative flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
						{item.linked_task_id && (
							<motion.button
								whileHover={{ scale: 1.1, zIndex: 10 }}
								whileTap={{ scale: 0.9 }}
								onClick={(e) => {
									e.stopPropagation()
									onDuplicateEntry(item)
								}}
								className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-white hover:bg-[var(--color-primary-surface)] transition-all"
								data-tooltip-id="journal-tooltip"
								data-tooltip-content="Duplicate Task"
							>
								<IconCopy size={14} />
							</motion.button>
						)}
						<motion.button
							whileHover={{ scale: 1.1, zIndex: 10 }}
							whileTap={{ scale: 0.9 }}
							onClick={(e) => {
								e.stopPropagation()
								onEditEntry(item)
							}}
							className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-white hover:bg-[var(--color-primary-surface)] transition-all"
							data-tooltip-id="journal-tooltip"
							data-tooltip-content="Edit"
						>
							<IconPencil size={14} />
						</motion.button>
						<motion.button
							whileHover={{ scale: 1.1, zIndex: 10 }}
							whileTap={{ scale: 0.9 }}
							onClick={(e) => {
								e.stopPropagation()
								onDeleteEntry(item)
							}}
							className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-accent-red)] hover:bg-[var(--color-accent-red)]/10 transition-all"
							data-tooltip-id="journal-tooltip"
							data-tooltip-content="Delete"
						>
							<IconTrash size={14} />
						</motion.button>
					</div>
				)}
			</div>
		</motion.div>
	)
}

export default JournalEntryCard
