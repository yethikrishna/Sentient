// A new file: src/client/components/tasks/EditTaskModal.js
"use client"

import React, { useState, useEffect } from "react"
import toast from "react-hot-toast"
import { motion } from "framer-motion"
import {
	IconX,
	IconGripVertical,
	IconPlus,
	IconLoader,
	IconSparkles,
	IconUser
} from "@tabler/icons-react"
import ScheduleEditor from "@components/tasks/ScheduleEditor"
import ConnectToolButton from "@components/tasks/ConnectToolButton"
import { cn } from "@utils/cn"

const EditTaskModal = ({
	task,
	onClose,
	onSave,
	setTask,
	integrations,
	allTools
}) => {
	const [isSubmitting, setIsSubmitting] = useState(false)

	// Use local state for editing, and update parent on save
	const [localTask, setLocalTask] = useState(task)
	useEffect(() => {
		setLocalTask(task)
	}, [task])

	const handleAddStep = () => {
		const newPlan = [
			...(localTask.plan || []),
			{ tool: "", description: "" }
		]
		setLocalTask({ ...localTask, plan: newPlan })
	}

	const handleRemoveStep = (index) => {
		const newPlan = localTask.plan.filter((_, i) => i !== index)
		setLocalTask({ ...localTask, plan: newPlan })
	}

	const handleStepChange = (index, field, value) => {
		const newPlan = [...localTask.plan]
		newPlan[index][field] = value
		setLocalTask({ ...localTask, plan: newPlan })
	}

	const handleFieldChange = (field, value) => {
		setLocalTask({ ...localTask, [field]: value })
	}

	const handleScheduleChange = (newSchedule) => {
		setLocalTask({ ...localTask, schedule: newSchedule })
	}

	const handleSubmit = async () => {
		setIsSubmitting(true)
		try {
			await onSave(localTask)
			onClose()
		} catch (error) {
			// onSave is expected to handle its own toasts
		} finally {
			setIsSubmitting(false)
		}
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={onClose}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-dark-surface p-6 rounded-2xl shadow-xl w-full max-w-3xl border border-dark-surface-elevated max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-6">
					<h3 className="text-xl font-semibold text-white">
						Edit Task
					</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-2 space-y-6">
					{/* Plan Details */}
					<div>
						<label className="text-sm font-medium text-gray-300 mb-2 block">
							Goal & Priority
						</label>
						<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
							<input
								type="text"
								value={localTask.description}
								onChange={(e) =>
									handleFieldChange(
										"description",
										e.target.value
									)
								}
								className="md:col-span-2 p-3 bg-dark-bg border border-dark-surface-elevated rounded-lg"
							/>
							<select
								value={localTask.priority}
								onChange={(e) =>
									handleFieldChange(
										"priority",
										Number(e.target.value)
									)
								}
								className="p-3 bg-dark-bg border border-dark-surface-elevated rounded-lg appearance-none"
							>
								<option value={0}>High Priority</option>
								<option value={1}>Medium Priority</option>
								<option value={2}>Low Priority</option>
							</select>
						</div>
					</div>

					{/* Plan Steps */}
					<div className="space-y-3">
						<label className="text-sm font-medium text-gray-300">
							Plan Steps
						</label>
						{(localTask.plan || []).map((step, index) => (
							<motion.div
								key={index}
								layout
								className="flex items-start gap-3"
							>
								<IconGripVertical className="h-5 w-5 text-gray-500 mt-2.5" />
								<div className="flex-grow flex flex-col gap-2">
									<div className="flex items-center gap-2">
										<select
											value={step.tool || ""}
											onChange={(e) =>
												handleStepChange(
													index,
													"tool",
													e.target.value
												)
											}
											className="w-2/5 p-2 bg-dark-bg border border-dark-surface-elevated rounded-md text-sm"
										>
											<option value="">
												Select tool...
											</option>
											{allTools.map((tool) => (
												<option
													key={tool.name}
													value={tool.name}
												>
													{tool.display_name}
												</option>
											))}
										</select>
										<input
											type="text"
											value={step.description}
											onChange={(e) =>
												handleStepChange(
													index,
													"description",
													e.target.value
												)
											}
											className="flex-grow p-2 bg-dark-bg border border-dark-surface-elevated rounded-md text-sm"
										/>
										<button
											type="button"
											onClick={() =>
												handleRemoveStep(index)
											}
											className="p-2 text-red-400 hover:bg-red-400/20 rounded-full"
										>
											<IconX size={16} />
										</button>
									</div>
								</div>
							</motion.div>
						))}
						<button
							type="button"
							onClick={handleAddStep}
							className="flex items-center gap-1.5 py-1.5 px-3 rounded-full bg-dark-surface-elevated hover:bg-dark-surface text-xs"
						>
							<IconPlus size={14} /> Add Step
						</button>
					</div>

					{/* Assignee */}
					<div>
						<label className="text-sm font-medium text-gray-300 mb-2 block">
							Assignee
						</label>
						<div className="flex gap-2 p-1 bg-dark-bg rounded-lg border border-dark-surface-elevated">
							<button
								onClick={() =>
									handleFieldChange("assignee", "ai")
								}
								className={cn(
									"flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm transition-colors",
									localTask.assignee === "ai"
										? "bg-[var(--color-accent-blue)] text-white"
										: "hover:bg-dark-surface"
								)}
							>
								<IconSparkles size={16} /> Sentient
							</button>
							<button
								onClick={() =>
									handleFieldChange("assignee", "user")
								}
								className={cn(
									"flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm transition-colors",
									localTask.assignee === "user"
										? "bg-[var(--color-accent-blue)] text-white"
										: "hover:bg-dark-surface"
								)}
							>
								<IconUser size={16} /> Me
							</button>
						</div>
					</div>

					{/* Schedule */}
					<div>
						<label className="text-sm font-medium text-gray-300 mb-2 block">
							Schedule
						</label>
						<ScheduleEditor
							schedule={
								localTask.schedule || {
									type: "once",
									run_at: null
								}
							}
							setSchedule={handleScheduleChange}
						/>
					</div>
				</div>
				<div className="flex justify-end gap-4 mt-6 pt-4 border-t border-dark-surface-elevated">
					<button
						onClick={onClose}
						className="py-2.5 px-5 rounded-lg bg-dark-surface-elevated hover:bg-dark-surface text-sm"
					>
						Cancel
					</button>
					<button
						onClick={handleSubmit}
						disabled={isSubmitting}
						className="py-2.5 px-5 rounded-lg bg-sentient-blue hover:bg-sentient-blue-dark text-sm flex items-center gap-2"
					>
						{isSubmitting && <IconLoader size={16} />}
						{isSubmitting ? "Saving..." : "Save Changes"}
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

export default EditTaskModal
