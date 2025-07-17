// A new file: src/client/components/tasks/EditTaskModal.js
"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import { IconX, IconGripVertical, IconPlugConnected } from "@tabler/icons-react"
import { useRouter } from "next/navigation"
import ScheduleEditor from "@components/tasks/ScheduleEditor"

const ConnectToolButton = ({ toolName }) => {
	const router = useRouter()
	return (
		<button
			type="button"
			onClick={() => router.push(`/settings`)}
			className="text-xs self-start bg-yellow-500/20 text-yellow-300 font-semibold py-1 px-2 rounded-full hover:bg-yellow-500/40 transition-colors whitespace-nowrap flex items-center gap-1"
		>
			<IconPlugConnected size={12} />
			Connect {toolName}
		</button>
	)
}

const PlanEditor = ({
	description,
	setDescription,
	priority,
	setPriority,
	plan,
	setPlan,
	schedule,
	setSchedule,
	allTools,
	integrations
}) => {
	const handleAddStep = () =>
		setPlan([...plan, { tool: "", description: "" }])
	const handleRemoveStep = (index) =>
		setPlan(plan.filter((_, i) => i !== index))
	const handleStepChange = (index, field, value) => {
		const newPlan = [...plan]
		newPlan[index][field] = value
		setPlan(newPlan)
	}

	return (
		<>
			<div>
				<label className="text-sm font-medium text-gray-300 mb-2 block">
					Plan Details
				</label>
				<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
					<input
						type="text"
						placeholder="Describe the overall goal..."
						value={description}
						onChange={(e) => setDescription(e.target.value)}
						className="md:col-span-2 p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg transition-colors focus:border-[var(--color-accent-blue)]"
					/>
					<select
						value={priority}
						onChange={(e) => setPriority(Number(e.target.value))}
						className="p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg appearance-none transition-colors focus:border-[var(--color-accent-blue)]"
					>
						<option value={0}>High Priority</option>
						<option value={1}>Medium Priority</option>
						<option value={2}>Low Priority</option>
					</select>
				</div>
			</div>
			<div className="space-y-3">
				<label className="text-sm font-medium text-gray-300">
					Plan Steps
				</label>
				{plan.map((step, index) => (
					<motion.div
						key={index}
						layout
						initial={{ opacity: 0, y: -10 }}
						animate={{ opacity: 1, y: 0 }}
						exit={{ opacity: 0, x: -20 }}
						className="flex items-start gap-2 sm:gap-3"
					>
						<IconGripVertical className="h-5 w-5 text-gray-500 flex-shrink-0 mt-2" />
						<div className="flex-grow flex flex-col gap-2">
							<div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
								<select
									value={step.tool || ""}
									onChange={(e) =>
										handleStepChange(
											index,
											"tool",
											e.target.value
										)
									}
									className="w-full sm:w-2/5 p-2 bg-neutral-800/50 border border-neutral-700 rounded-md text-sm transition-colors focus:border-[var(--color-accent-blue)]"
								>
									<option value="">Select a tool...</option>
									{allTools.map((tool) => {
										const isConnected =
											integrations.find(
												(i) => i.name === tool.name
											)?.connected ||
											integrations.find(
												(i) => i.name === tool.name
											)?.auth_type === "builtin"
										return (
											<option
												key={tool.name}
												value={tool.name}
											>
												{tool.display_name}{" "}
												{!isConnected &&
													" (Not Connected)"}
											</option>
										)
									})}
								</select>
								<input
									type="text"
									placeholder="Describe what this step should do..."
									value={step.description}
									onChange={(e) =>
										handleStepChange(
											index,
											"description",
											e.target.value
										)
									}
									className="flex-grow p-2 bg-neutral-800/50 border border-neutral-700 rounded-md text-sm transition-colors focus:border-[var(--color-accent-blue)]"
								/>
								<button
									type="button"
									onClick={() => handleRemoveStep(index)}
									className="p-2 text-[var(--color-accent-red)] hover:bg-neutral-700 rounded-full"
								>
									<IconX className="h-4 w-4" />
								</button>
							</div>
							{!integrations.find((i) => i.name === step.tool)
								?.connected &&
								integrations.find((i) => i.name === step.tool)
									?.auth_type !== "builtin" &&
								step.tool && (
									<ConnectToolButton toolName={step.tool} />
								)}
						</div>
					</motion.div>
				))}
				<button
					type="button"
					onClick={handleAddStep}
					className="flex items-center gap-1.5 py-1.5 px-3 rounded-full bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-xs"
				>
					<IconGripVertical className="h-4 w-4" /> Add Step
				</button>
			</div>
			<div>
				<label className="text-sm font-medium text-gray-300 mb-2 block">
					Schedule
				</label>
				<ScheduleEditor schedule={schedule} setSchedule={setSchedule} />
			</div>
		</>
	)
}

const EditTaskModal = ({
	task,
	onClose,
	onSave,
	setTask,
	allTools,
	integrations
}) => {
	const safeSchedule = task.schedule || { type: "once", run_at: null }
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
