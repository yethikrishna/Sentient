"use client"

import React from "react"
import { motion } from "framer-motion"
import { Tooltip } from "react-tooltip"
import { IconX } from "@tabler/icons-react"
import TaskDetailsContent from "./TaskDetailsContent"

const TaskDetailsModal = ({ task, onClose }) => {
	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<Tooltip id="task-details-tooltip" />
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-3xl border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-6">
					<h3 className="text-2xl font-semibold text-white truncate">
						{task.description}
					</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-2 space-y-6">
					<div className="flex items-center gap-4 text-sm">
						<span className="text-[var(--color-text-secondary)]">
							<TaskDetailsContent task={task} />
						</span>
					</div>
				</div>
			</motion.div>
		</motion.div>
	)
}

export default TaskDetailsModal
