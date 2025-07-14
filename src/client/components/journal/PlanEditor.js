"use client"

import React from "react"
import { AnimatePresence, motion } from "framer-motion"
import { IconGripVertical, IconX, IconPlus } from "@tabler/icons-react"
import ConnectToolButton from "./ConnectToolButton"
import ScheduleEditor from "./ScheduleEditor"

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
				<AnimatePresence>
					{plan.map((step, index) => (
						<motion.div
							key={index}
							layout
							initial={{ opacity: 0, y: -10 }}
							animate={{ opacity: 1, y: 0 }}
							exit={{ opacity: 0, x: -20 }}
							className="flex items-start gap-2 sm:gap-3"
						>
							<IconGripVertical className="h-5 w-5 text-gray-500 flex-shrink-0" />
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
										<option value="">
											Select a tool...
										</option>
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
										onClick={() => handleRemoveStep(index)}
										className="p-2 text-[var(--color-accent-red)] hover:bg-neutral-700 rounded-full"
									>
										<IconX className="h-4 w-4" />
									</button>
								</div>
								{!integrations.find((i) => i.name === step.tool)
									?.connected &&
									integrations.find(
										(i) => i.name === step.tool
									)?.auth_type !== "builtin" &&
									step.tool && (
										<ConnectToolButton
											toolName={step.tool}
										/>
									)}
							</div>
						</motion.div>
					))}
				</AnimatePresence>
				<button
					onClick={handleAddStep}
					className="flex items-center gap-1.5 py-1.5 px-3 rounded-full bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-xs"
				>
					<IconPlus className="h-4 w-4" /> Add Step
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

export default PlanEditor
