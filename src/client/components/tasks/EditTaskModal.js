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
	onSave, // Expects a function that takes the updated task
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
		setLocalTask((prev) => ({
			...prev,
			plan: prev.plan.filter((_, i) => i !== index)
		}))
	}

	const handleStepChange = (index, field, value) => {
		setLocalTask((prev) => ({
			...prev,
			plan: prev.plan.map((step, i) =>
				i === index ? { ...step, [field]: value } : step
			)
		}))
	}

	const handleFieldChange = (field, value) => {
		setLocalTask((prev) => ({ ...prev, [field]: value }))
	}

	const handleScheduleChange = (newSchedule) => {
		setLocalTask((prev) => ({ ...prev, schedule: newSchedule }))
	}

	const handleSubmit = async () => {
		setIsSubmitting(true)
		try {
			// onSave is now the function from the parent that handles the API call and closes the modal.
			await onSave(localTask)
		} catch (error) {
			// Errors are handled by the `handleAction` wrapper in the parent component.
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
			className="fixed inset-0 bg-black/70 backdrop-blur-2xl flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.8, y: 40, opacity: 0 }}
				animate={{ scale: 1, y: 0, opacity: 1 }}
				exit={{ scale: 0.8, y: 40, opacity: 0 }}
				transition={{ type: "spring", duration: 0.6, bounce: 0.3 }}
				onClick={(e) => e.stopPropagation()}
				className="relative bg-gradient-to-br from-white/15 via-white/10 to-white/15 p-8 rounded-3xl shadow-2xl w-full max-w-4xl border border-white/20 max-h-[90vh] flex flex-col backdrop-blur-2xl overflow-hidden"
			>
				<div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-purple-500/5 to-pink-500/10 rounded-3xl" />
				<div className="absolute inset-0 backdrop-blur-3xl bg-black/20 rounded-3xl border border-white/10 shadow-inner" />
				<div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-blue-400/20 to-purple-400/20 rounded-full blur-2xl animate-pulse" />
				<div className="absolute -bottom-4 -left-4 w-32 h-32 bg-gradient-to-br from-purple-400/20 to-pink-400/20 rounded-full blur-2xl animate-pulse" />
			
				<div className="relative flex justify-between items-center mb-8 z-10">
					<div>
						<h3 className="text-3xl font-bold bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent drop-shadow-2xl">
							✏️ Edit Task
						</h3>
						<div className="w-1/3 h-1 bg-gradient-to-r from-blue-500/50 via-purple-500/50 to-pink-500/50 rounded-full blur-sm mt-2" />
					</div>
					<button 
						onClick={onClose} 
						className="relative p-3 rounded-2xl bg-white/10 hover:bg-white/20 backdrop-blur-lg border border-white/20 hover:border-white/30 transition-all duration-300 transform hover:scale-110 shadow-lg group"
					>
						<IconX className="text-white/70 group-hover:text-white transition-colors" />
					</button>
				</div>
				<div className="relative overflow-y-auto custom-scrollbar pr-2 space-y-8 z-10">
					{/* Plan Details */}
					<div className="relative p-6 bg-gradient-to-br from-white/10 via-white/5 to-white/10 rounded-2xl border border-white/20 backdrop-blur-xl shadow-xl">
						<div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5 rounded-2xl" />
						<div className="relative z-10">
							<label className="text-lg font-bold text-white mb-4 block drop-shadow-lg">
								🎯 Goal & Priority
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
									className="md:col-span-2 p-4 bg-gradient-to-r from-white/10 to-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 backdrop-blur-lg shadow-lg focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400/50 transition-all duration-300"
									placeholder="Task description..."
								/>
								<select
									value={localTask.priority}
									onChange={(e) =>
										handleFieldChange(
											"priority",
											Number(e.target.value)
										)
									}
									className="p-4 bg-gradient-to-r from-white/10 to-white/5 border border-white/20 rounded-xl text-white backdrop-blur-lg shadow-lg focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400/50 transition-all duration-300 appearance-none"
								>
									<option value={0} className="bg-gray-900">🔴 High Priority</option>
									<option value={1} className="bg-gray-900">🟡 Medium Priority</option>
									<option value={2} className="bg-gray-900">🟢 Low Priority</option>
								</select>
							</div>
						</div>
					</div>

					{/* Plan Steps */}
					<div className="relative p-6 bg-gradient-to-br from-white/10 via-white/5 to-white/10 rounded-2xl border border-white/20 backdrop-blur-xl shadow-xl space-y-4">
						<div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-pink-500/5 rounded-2xl" />
						<div className="relative z-10">
							<label className="text-lg font-bold text-white mb-4 block drop-shadow-lg">
								📋 Plan Steps
							</label>
							{(localTask.plan || []).map((step, index) => (
								<motion.div
									key={index}
									layout
									className="flex items-start gap-4 p-4 bg-gradient-to-r from-white/10 to-white/5 rounded-xl border border-white/20 backdrop-blur-lg shadow-lg"
								>
									<IconGripVertical className="h-6 w-6 text-white/50 mt-2 drop-shadow-lg" />
									<div className="flex-grow flex flex-col gap-3">
										<div className="flex items-center gap-3">
											<select
												value={step.tool || ""}
												onChange={(e) =>
													handleStepChange(
														index,
														"tool",
														e.target.value
													)
												}
												className="w-2/5 p-3 bg-gradient-to-r from-white/10 to-white/5 border border-white/20 rounded-xl text-white backdrop-blur-lg shadow-lg focus:ring-2 focus:ring-purple-400/50 focus:border-purple-400/50 transition-all duration-300"
											>
												<option value="" className="bg-gray-900">
													Select tool...
												</option>
												{allTools.map((tool) => (
													<option
														key={tool.name}
														value={tool.name}
														className="bg-gray-900"
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
												className="flex-grow p-3 bg-gradient-to-r from-white/10 to-white/5 border border-white/20 rounded-xl text-white placeholder-white/50 backdrop-blur-lg shadow-lg focus:ring-2 focus:ring-purple-400/50 focus:border-purple-400/50 transition-all duration-300"
												placeholder="Step description..."
											/>
											<button
												type="button"
												onClick={() =>
													handleRemoveStep(index)
												}
												className="p-3 text-red-400 hover:bg-red-500/20 rounded-xl backdrop-blur-lg border border-red-400/30 hover:border-red-400/50 transition-all duration-300 transform hover:scale-110 shadow-lg"
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
								className="flex items-center gap-2 py-3 px-6 rounded-2xl bg-gradient-to-r from-purple-500/20 to-pink-500/20 hover:from-purple-500/30 hover:to-pink-500/30 text-white backdrop-blur-lg border border-purple-400/30 transition-all duration-300 transform hover:scale-105 shadow-lg font-medium"
							>
								<IconPlus size={16} /> ✨ Add Step
							</button>
						</div>
					</div>

					{/* Assignee */}
					<div className="relative p-6 bg-gradient-to-br from-white/10 via-white/5 to-white/10 rounded-2xl border border-white/20 backdrop-blur-xl shadow-xl">
						<div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-cyan-500/5 rounded-2xl" />
						<div className="relative z-10">
							<label className="text-lg font-bold text-white mb-4 block drop-shadow-lg">
								👤 Assignee
							</label>
							<div className="flex gap-3 p-2 bg-gradient-to-r from-white/10 to-white/5 rounded-2xl border border-white/20 backdrop-blur-lg shadow-lg">
								<button
									onClick={() =>
										handleFieldChange("assignee", "ai")
									}
									className={cn(
										"flex-1 flex items-center justify-center gap-3 py-4 rounded-xl text-sm transition-all duration-300 font-semibold backdrop-blur-lg border",
										localTask.assignee === "ai"
											? "bg-gradient-to-r from-blue-500 to-purple-500 text-white border-blue-400/50 shadow-lg shadow-blue-500/25"
											: "hover:bg-white/10 text-white/70 border-white/20 hover:border-white/30"
									)}
								>
									<IconSparkles size={18} /> ✨ Sentient
								</button>
								<button
									onClick={() =>
										handleFieldChange("assignee", "user")
									}
									className={cn(
										"flex-1 flex items-center justify-center gap-3 py-4 rounded-xl text-sm transition-all duration-300 font-semibold backdrop-blur-lg border",
										localTask.assignee === "user"
											? "bg-gradient-to-r from-blue-500 to-purple-500 text-white border-blue-400/50 shadow-lg shadow-blue-500/25"
											: "hover:bg-white/10 text-white/70 border-white/20 hover:border-white/30"
									)}
								>
									<IconUser size={18} /> 👨‍💻 Me
								</button>
							</div>
						</div>
					</div>

					{/* Schedule */}
					<div className="relative p-6 bg-gradient-to-br from-white/10 via-white/5 to-white/10 rounded-2xl border border-white/20 backdrop-blur-xl shadow-xl">
						<div className="absolute inset-0 bg-gradient-to-br from-green-500/5 via-transparent to-emerald-500/5 rounded-2xl" />
						<div className="relative z-10">
							<label className="text-lg font-bold text-white mb-4 block drop-shadow-lg">
								📅 Schedule
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
				</div>
				<div className="relative flex justify-end gap-4 mt-8 pt-6 border-t border-white/20 z-10">
					<button
						onClick={onClose}
						className="py-4 px-8 rounded-2xl bg-gradient-to-r from-white/10 to-white/5 hover:from-white/15 hover:to-white/10 text-white backdrop-blur-lg border border-white/20 hover:border-white/30 transition-all duration-300 font-medium shadow-lg transform hover:scale-105"
					>
						Cancel
					</button>
					<button
						onClick={handleSubmit}
						disabled={isSubmitting}
						className="py-4 px-8 rounded-2xl bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 hover:shadow-2xl hover:shadow-blue-500/25 text-white font-semibold flex items-center gap-3 backdrop-blur-lg border border-white/20 transition-all duration-300 transform hover:scale-105 disabled:opacity-50"
					>
						{isSubmitting && <IconLoader size={18} className="animate-spin" />}
						{isSubmitting ? "💾 Saving..." : "✨ Save Changes"}
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

export default EditTaskModal
