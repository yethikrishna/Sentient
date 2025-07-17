"use client"

import React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@utils/cn"
import { IconChevronLeft } from "@tabler/icons-react"
import TaskOverviewCard from "./TaskOverviewCard"

const CollapsibleSection = ({
	title,
	tasks,
	isOpen,
	toggleOpen,
	integrations,
	...handlers
}) => {
	if (!tasks || tasks.length === 0) return null
	return (
		<div>
			<button
				onClick={toggleOpen}
				className="w-full flex justify-between items-center py-2 px-1 text-left hover:bg-[var(--color-primary-surface)]/50 rounded-lg transition-colors"
			>
				<h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
					{title} ({tasks.length})
				</h2>
				<IconChevronLeft
					className={cn(
						"transform transition-transform duration-200",
						isOpen ? "-rotate-90" : "rotate-0"
					)}
				/>
			</button>
			<AnimatePresence>
				{isOpen && (
					<motion.div
						initial={{ height: 0, opacity: 0 }}
						animate={{ height: "auto", opacity: 1 }}
						exit={{ height: 0, opacity: 0 }}
						className="overflow-hidden"
					>
						<div className="space-y-2 pt-2 pb-2">
							{tasks.map((task) => (
								<TaskOverviewCard
									key={task.task_id}
									task={task}
									integrations={integrations}
									{...handlers}
								/>
							))}
						</div>
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	)
}

export default CollapsibleSection
