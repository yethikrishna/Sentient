"use client"

import React from "react"
import { motion } from "framer-motion"
import { IconX } from "@tabler/icons-react"
import PlanEditor from "./PlanEditor"

const EditTaskModal = ({
	task,
	onClose,
	onSave,
	setTask,
	allTools,
	integrations,
	onUpdateSchedule
}) => {
	const safeSchedule = task.schedule || { type: "once", run_at: null }
	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-3xl border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-6">
					<h3 className="text-xl font-semibold">Edit Task</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-2 space-y-6">
					<PlanEditor
						description={task.description}
						setDescription={(val) =>
							setTask({ ...task, description: val })
						}
						priority={task.priority}
						setPriority={(val) =>
							setTask({ ...task, priority: val })
						}
						plan={task.plan}
						setPlan={(val) => setTask({ ...task, plan: val })}
						schedule={safeSchedule}
						setSchedule={(val) => {
							onUpdateSchedule(task.task_id, val)
							setTask({ ...task, schedule: val })
						}}
						allTools={allTools}
						integrations={integrations}
					/>
				</div>
				<div className="flex justify-end gap-4 mt-6 pt-4 border-t border-neutral-700">
					<button
						onClick={onClose}
						className="py-2.5 px-5 rounded-lg bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-sm"
					>
						Cancel
					</button>
					<button
						onClick={onSave}
						className="py-2.5 px-5 rounded-lg bg-[var(--color-accent-green)] hover:bg-[var(--color-accent-green-hover)] text-sm transition-colors"
					>
						Save Changes
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

export default EditTaskModal
