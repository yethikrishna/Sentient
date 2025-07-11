"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import {
	IconLoader,
	IconPencil,
	IconTrash,
	IconX,
	IconHelpCircle,
	IconSearch,
	IconRefresh,
	IconClock,
	IconPlayerPlay,
	IconCircleCheck,
	IconMailQuestion,
	IconAlertTriangle,
	IconAlertCircle,
	IconFilter,
	IconChevronUp,
	IconPlus,
	IconGripVertical,
	IconBrain,
	IconBook,
	IconMail,
	IconCalendarEvent,
	IconMessage,
	IconArrowRight,
	IconPlugConnected,
	IconChevronDown,
	IconChecklist
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { Tooltip } from "react-tooltip"
import "react-tooltip/dist/react-tooltip.css"
import { cn } from "@utils/cn"
import { motion, AnimatePresence } from "framer-motion"
import { useRouter } from "next/navigation"

const statusMap = {
	pending: {
		icon: IconClock,
		color: "text-yellow-500",
		borderColor: "border-yellow-500",
		label: "Pending"
	},
	processing: {
		icon: IconPlayerPlay,
		color: "text-blue-500",
		borderColor: "border-blue-500",
		label: "Processing"
	},
	completed: {
		icon: IconCircleCheck,
		color: "text-green-500",
		borderColor: "border-green-500",
		label: "Completed"
	},
	error: {
		icon: IconAlertCircle,
		color: "text-red-500",
		borderColor: "border-red-500",
		label: "Error"
	},
	approval_pending: {
		icon: IconMailQuestion,
		color: "text-purple-500",
		borderColor: "border-purple-500",
		label: "Approval Pending"
	},
	active: {
		icon: IconRefresh,
		color: "text-green-500",
		label: "Active"
	},
	cancelled: {
		icon: IconX,
		color: "text-gray-500",
		borderColor: "border-gray-500",
		label: "Cancelled"
	},
	default: {
		icon: IconHelpCircle,
		color: "text-gray-400",
		borderColor: "border-gray-400",
		label: "Unknown"
	}
}

const priorityMap = {
	0: { label: "High", color: "text-red-400" },
	1: { label: "Medium", color: "text-yellow-400" },
	2: { label: "Low", color: "text-green-400" },
	default: { label: "Unknown", color: "text-gray-400" }
}

const Tasks = () => {
	const [tasks, setTasks] = useState([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)
	const [editingTask, setEditingTask] = useState(null)
	const [filterStatus, setFilterStatus] = useState("all")
	const [isGeneratingPlan, setIsGeneratingPlan] = useState(false)
	const [searchTerm, setSearchTerm] = useState("")
	const [viewingTask, setViewingTask] = useState(null)
	const [isCreatePlanOpen, setCreatePlanOpen] = useState(false)
	const [createStep, setCreateStep] = useState("generate") // 'generate' or 'review'
	const [openSections, setOpenSections] = useState({
		// By default, only show sections that are likely to need action
		// The user can expand the others if needed.
		// This improves the initial view by reducing clutter.
		active: false, // Recurring tasks are less frequently managed
		approval_pending: true,
		processing: true,
		completed: true
	})
	const [isAdding, setIsAdding] = useState(false)
	const [generationPrompt, setGenerationPrompt] = useState("")
	const [newTaskDescription, setNewTaskDescription] = useState("")
	const [newTaskPriority, setNewTaskPriority] = useState(1)
	const [newTaskPlan, setNewTaskPlan] = useState([])
	const [newSchedule, setNewSchedule] = useState({
		type: "once",
		run_at: null,
		frequency: "daily",
		time: "09:00",
		days: []
	})
	const [allTools, setAllTools] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [loadingIntegrations, setLoadingIntegrations] = useState(true)

	const fetchTasksData = useCallback(async () => {
		setError(null)
		try {
			const response = await fetch("/api/tasks")
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to fetch tasks")
			if (Array.isArray(data.tasks)) {
				const sortedTasks = data.tasks.sort((a, b) => {
					const statusOrder = {
						active: -2,
						approval_pending: -1,
						processing: 0,
						pending: 1,
						error: 2,
						cancelled: 3,
						completed: 4
					}
					const statusA = statusOrder[a.status] ?? 99
					const statusB = statusOrder[b.status] ?? 99
					if (statusA !== statusB) return statusA - statusB
					if (a.priority !== b.priority)
						return a.priority - b.priority
					try {
						const dateA = a.created_at
							? new Date(a.created_at).getTime()
							: 0
						const dateB = b.created_at
							? new Date(b.created_at).getTime()
							: 0
						return dateB - dateA
					} catch (dateError) {
						return 0
					}
				})
				setTasks(sortedTasks)
			} else {
				throw new Error("Invalid tasks response format")
			}
		} catch (err) {
			setError("Failed to fetch tasks: " + err.message)
			setTasks([])
		} finally {
			setLoading(false)
		}
	}, [])

	const fetchAllToolsAndIntegrations = async () => {
		setLoadingIntegrations(true)
		try {
			const response = await fetch("/api/settings/integrations")
			if (!response.ok)
				throw new Error("Failed to fetch integrations status")
			const data = await response.json()
			const allIntegrations = data.integrations || []
			setIntegrations(allIntegrations)
			const tools = allIntegrations.map((i) => ({
				name: i.name,
				display_name: i.display_name
			}))
			setAllTools(tools)
		} catch (error) {
			toast.error(error.message)
			setIntegrations([])
			setAllTools([])
		} finally {
			setLoadingIntegrations(false)
		}
	}

	useEffect(() => {
		fetchTasksData()
		fetchAllToolsAndIntegrations()
		const intervalId = setInterval(fetchTasksData, 60000)
		return () => clearInterval(intervalId)
	}, [fetchTasksData])

	const handleGeneratePlan = async () => {
		if (!generationPrompt.trim()) {
			toast.error("Please enter a goal for your plan.")
			return
		}
		setIsGeneratingPlan(true)
		try {
			const response = await fetch("/api/tasks/generate-plan", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ prompt: generationPrompt })
			})
			const data = await response.json()
			if (!response.ok) throw new Error(data.detail)
			if (!data.plan || data.plan.length === 0) {
				toast.error(
					"The agent could not generate a plan for this goal. Please try rephrasing."
				)
			} else {
				setNewTaskDescription(data.description || generationPrompt)
				setNewTaskPlan(data.plan)
				setCreateStep("review")
				toast.success("Plan generated! Review and save it below.")
			}
		} catch (error) {
			toast.error(`Plan Generation Failed: ${error.message}`)
		} finally {
			setIsGeneratingPlan(false)
		}
	}

	const handleUpdateTaskSchedule = async (taskId, schedule) => {
		if (!taskId) return false
		try {
			const response = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId, schedule })
			})
			if (!response.ok) throw new Error((await response.json()).error)
			toast.success("Task schedule updated!")
			await fetchTasksData() // Refresh data
			return true // Indicate success
		} catch (error) {
			toast.error(`Failed to update schedule: ${error.message}`)
			return false
		}
	}

	const handleAddTask = async () => {
		if (!newTaskDescription.trim())
			return toast.error("Please enter a task description.")
		if (newTaskPlan.some((step) => !step.tool || !step.description.trim()))
			return toast.error(
				"All plan steps must have a tool and description."
			)
		setIsAdding(true)
		try {
			// Clean up schedule object before sending
			const schedulePayload =
				newSchedule.type === "once"
					? { type: "once", run_at: newSchedule.run_at || null }
					: newSchedule

			const taskData = {
				description: newTaskDescription,
				priority: newTaskPriority,
				plan: newTaskPlan,
				schedule: schedulePayload
			}

			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(taskData)
			})
			if (!response.ok) {
				const data = await response.json()
				throw new Error(data.error || "Failed to add task")
			}
			toast.success("New plan created successfully!")
			setGenerationPrompt("")
			setNewTaskDescription("")
			setNewTaskPriority(1)
			setNewTaskPlan([])
			setNewSchedule({
				type: "once",
				run_at: null,
				frequency: "daily",
				time: "09:00",
				days: []
			})
			setCreateStep("generate")
			setCreatePlanOpen(false)
			await fetchTasksData()
		} catch (error) {
			toast.error(`Failed to add task: ${error.message}`)
		} finally {
			setIsAdding(false)
		}
	}

	const handleEditTask = (task) => setEditingTask({ ...task })
	const handleUpdateTask = async () => {
		if (
			!editingTask ||
			!editingTask.description?.trim() ||
			editingTask.plan.some(
				(step) => !step.tool || !step.description?.trim()
			)
		) {
			return toast.error("Description and all plan steps are required.")
		}

		try {
			const schedulePayload =
				editingTask.schedule?.type === "once"
					? {
							type: "once",
							run_at: editingTask.schedule.run_at || null
						}
					: editingTask.schedule
			const response = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					taskId: editingTask.task_id,
					description: editingTask.description,
					priority: editingTask.priority,
					plan: editingTask.plan,
					schedule: schedulePayload
				})
			})
			if (!response.ok) throw new Error((await response.json()).error)
			toast.success("Task updated successfully!")
			setEditingTask(null)
			await fetchTasksData()
		} catch (error) {
			toast.error(`Failed to update task: ${error.message}`)
		}
	}
	const handleDeleteTask = async (taskId) => {
		if (!taskId || !window.confirm("Delete this task forever?")) return
		try {
			const response = await fetch("/api/tasks/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) throw new Error((await response.json()).error)
			toast.success("Task deleted!")
			setViewingTask(null)
			await fetchTasksData()
		} catch (error) {
			toast.error(`Failed to delete task: ${error.message}`)
		}
	}
	const handleApproveTask = async (taskId) => {
		if (!taskId) return
		try {
			const response = await fetch("/api/tasks/approve", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) {
				const errorData = await response.json()
				if (response.status === 409)
					toast.error(errorData.detail, { duration: 6000 })
				else throw new Error(errorData.error || "Approval failed")
			} else {
				toast.success("Plan approved and queued for execution.")
			}
			setViewingTask(null)
			await fetchTasksData()
		} catch (error) {
			toast.error(`Error approving task: ${error.message}`)
		}
	}
	const handleReRunTask = async (taskId) => {
		if (
			!taskId ||
			!window.confirm("Create a new copy of this task to run again?")
		)
			return
		try {
			const response = await fetch("/api/tasks/rerun", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) throw new Error((await response.json()).error)
			toast.success("Task duplicated for approval.")
			await fetchTasksData()
		} catch (error) {
			toast.error(`Failed to re-run task: ${error.message}`)
		}
	}

	const filteredTasks = tasks.filter(
		(task) =>
			(filterStatus === "all" || task.status === filterStatus) &&
			(!searchTerm ||
				task.description
					?.toLowerCase()
					.includes(searchTerm.toLowerCase()))
	)

	const groupedTasks = {
		active: filteredTasks.filter((t) => t.status === "active"),
		approval_pending: filteredTasks.filter(
			(t) => t.status === "approval_pending"
		),
		processing: filteredTasks.filter((t) =>
			["processing", "pending"].includes(t.status)
		),
		completed: filteredTasks.filter((t) =>
			["completed", "error", "cancelled"].includes(t.status)
		)
	}

	const toggleSection = (section) =>
		setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }))

	return (
		<div className="flex h-screen bg-gradient-to-br from-[var(--color-primary-background)] via-[var(--color-primary-background)] to-[var(--color-primary-surface)]/20 text-[var(--color-text-primary)] overflow-x-hidden pl-0 md:pl-20">
			<Tooltip id="tasks-tooltip" />
			<div className="flex-1 flex flex-col overflow-hidden h-screen">
				<motion.header
					initial={{ y: -20, opacity: 0 }}
					animate={{ y: 0, opacity: 1 }}
					transition={{ duration: 0.6, ease: "easeOut" }}
					className="flex items-center justify-between p-4 md:px-8 md:py-6 bg-[var(--color-primary-background)] border-b border-[var(--color-primary-surface)]"
				>
					<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)] flex items-center gap-3">
						Tasks
					</h1>
					<div className="w-full md:max-w-lg flex items-center space-x-2 sm:space-x-3 bg-[var(--color-primary-surface)]/80 backdrop-blur-sm rounded-full p-2 shadow-lg border border-[var(--color-primary-surface-elevated)]">
						<IconSearch className="h-5 w-5 text-gray-400 ml-2 flex-shrink-0" />
						<input
							type="text"
							placeholder="Search tasks by description..."
							value={searchTerm}
							onChange={(e) => setSearchTerm(e.target.value)}
							className="bg-transparent text-white focus:outline-none w-full px-1 sm:px-2 text-sm"
						/>
						<div className="relative flex-shrink-0">
							<select
								value={filterStatus}
								onChange={(e) =>
									setFilterStatus(e.target.value)
								}
								className="appearance-none bg-[var(--color-primary-surface-elevated)] border border-[var(--color-primary-surface-elevated)] text-white text-xs rounded-full pl-3 pr-8 py-1.5 focus:outline-none focus:border-[var(--color-accent-blue)] cursor-pointer"
							>
								<option value="all">All</option>
								<option value="active">Active</option>
								<option value="pending">Pending</option>
								<option value="processing">Processing</option>
								<option value="approval_pending">
									Approval
								</option>
								<option value="completed">Completed</option>
								<option value="error">Error</option>
								<option value="cancelled">Cancelled</option>
							</select>
							<IconFilter className="absolute right-2.5 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
						</div>
						<button
							onClick={() => fetchTasksData()}
							className="p-1.5 rounded-full hover:bg-[var(--color-primary-surface-elevated)] transition-colors text-gray-300"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Refresh task list"
							disabled={loading && tasks.length > 0}
						>
							{loading && tasks.length > 0 ? (
								<IconLoader className="h-5 w-5 animate-spin" />
							) : (
								<IconRefresh className="h-5 w-5" />
							)}
						</button>
					</div>
				</motion.header>

				<main className="flex-1 w-full max-w-3xl mx-auto flex flex-col overflow-y-auto custom-scrollbar px-4">
					<div className="space-y-2 pt-6 pb-36">
						{loading || loadingIntegrations ? (
							<div className="flex justify-center items-center h-full">
								<IconLoader className="w-12 h-12 animate-spin text-[var(--color-accent-blue)]" />
							</div>
						) : error ? (
							<div className="text-red-400 text-center py-20">
								{error}
							</div>
						) : filteredTasks.length === 0 ? (
							<p className="text-gray-500 text-center py-20 mt-5">
								No tasks found. Create a new plan below!
							</p>
						) : (
							<>
								<CollapsibleSection
									title="Active"
									tasks={groupedTasks.active}
									isOpen={openSections.active}
									toggleOpen={() => toggleSection("active")}
									onViewDetails={setViewingTask}
									onEditTask={handleEditTask}
									onDeleteTask={handleDeleteTask}
									onUpdateSchedule={handleUpdateTaskSchedule}
								/>
								<CollapsibleSection
									title="Pending Approval"
									tasks={groupedTasks.approval_pending}
									isOpen={openSections.approval_pending}
									toggleOpen={() =>
										toggleSection("approval_pending")
									}
									onViewDetails={setViewingTask}
									onEditTask={handleEditTask}
									onDeleteTask={handleDeleteTask}
									onApproveTask={handleApproveTask}
									onUpdateSchedule={handleUpdateTaskSchedule}
									integrations={integrations}
								/>
								<CollapsibleSection
									title="Processing"
									tasks={groupedTasks.processing}
									isOpen={openSections.processing}
									toggleOpen={() =>
										toggleSection("processing")
									}
									onViewDetails={setViewingTask}
								/>
								<CollapsibleSection
									title="Completed"
									tasks={groupedTasks.completed}
									isOpen={openSections.completed}
									toggleOpen={() =>
										toggleSection("completed")
									}
									onViewDetails={setViewingTask}
									onDeleteTask={handleDeleteTask}
									onReRunTask={handleReRunTask}
								/>
							</>
						)}
					</div>
				</main>

				<div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/50 via-neutral-900/80 to-transparent backdrop-blur-sm border-t border-neutral-700/50 z-20">
					<div className="max-w-3xl mx-auto">
						<div
							onClick={() => setCreatePlanOpen(!isCreatePlanOpen)}
							className="flex justify-between items-center cursor-pointer"
						>
							<h3 className="text-lg font-semibold text-white">
								Create a New Plan
							</h3>
							<IconChevronDown
								className={cn(
									"transform transition-transform duration-200",
									!isCreatePlanOpen && "rotate-180"
								)}
							/>
						</div>
						<AnimatePresence>
							{isCreatePlanOpen && (
								<motion.div
									key="create-plan-panel"
									initial={{ height: 0, opacity: 0 }}
									animate={{ height: "auto", opacity: 1 }}
									exit={{ height: 0, opacity: 0 }}
									className="overflow-hidden"
								>
									{createStep === "generate" ? (
										<div className="space-y-4 pt-4">
											<label className="text-sm font-medium text-gray-300 mb-1 block">
												What is your goal?
											</label>
											<textarea
												placeholder="e.g., Send a daily summary of my calendar to my boss"
												value={generationPrompt}
												onChange={(e) =>
													setGenerationPrompt(
														e.target.value
													)
												}
												rows={3}
												className="w-full p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 backdrop-blur-sm transition-colors"
											/>
											<div className="flex justify-end">
												<button
													onClick={handleGeneratePlan}
													disabled={isGeneratingPlan}
													className="p-3 px-6 bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] rounded-lg text-white font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
												>
													{isGeneratingPlan ? (
														<IconLoader className="w-5 h-5 animate-spin" />
													) : (
														<>
															Next: Review Plan{" "}
															<IconArrowRight className="w-4 h-4" />
														</>
													)}
												</button>
											</div>
										</div>
									) : (
										// REVIEW STEP
										<div className="space-y-6 pt-4">
											<PlanEditor
												description={newTaskDescription}
												setDescription={
													setNewTaskDescription
												}
												priority={newTaskPriority}
												setPriority={setNewTaskPriority}
												plan={newTaskPlan}
												setPlan={setNewTaskPlan}
												schedule={newSchedule}
												setSchedule={setNewSchedule}
												allTools={allTools}
												integrations={integrations}
											/>
											<div className="flex justify-between items-center">
												<button
													onClick={() =>
														setCreateStep(
															"generate"
														)
													}
													className="py-2.5 px-6 rounded-lg bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-white text-sm font-semibold"
												>
													Back
												</button>
												<button
													onClick={handleAddTask}
													disabled={isAdding}
													className="py-2.5 px-6 rounded-lg bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
												>
													{isAdding && (
														<IconLoader className="h-5 h-5 animate-spin" />
													)}
													Save New Plan
												</button>
											</div>
										</div>
									)}
								</motion.div>
							)}
						</AnimatePresence>
					</div>
				</div>
			</div>
			{viewingTask && (
				<TaskDetailsModal
					task={viewingTask}
					onClose={() => setViewingTask(null)}
					onApprove={handleApproveTask}
					integrations={integrations}
				/>
			)}
			{editingTask && (
				<EditTaskModal
					task={editingTask}
					onClose={() => setEditingTask(null)}
					onSave={handleUpdateTask}
					setTask={setEditingTask}
					onUpdateSchedule={handleUpdateTaskSchedule}
					allTools={allTools}
					integrations={integrations}
				/>
			)}
		</div>
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

const EditTaskModal = ({
	task,
	onClose,
	onSave,
	setTask,
	onUpdateSchedule,
	allTools,
	integrations
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

const ConnectToolButton = ({ toolName }) => {
	const router = useRouter()
	return (
		<button
			onClick={() => router.push(`/settings`)}
			className="text-xs self-start bg-yellow-500/20 text-yellow-300 font-semibold py-1 px-2 rounded-full hover:bg-yellow-500/40 transition-colors whitespace-nowrap flex items-center gap-1"
		>
			<IconPlugConnected size={12} />
			Connect {toolName}
		</button>
	)
}

const CollapsibleSection = ({
	title,
	tasks,
	isOpen,
	toggleOpen,
	...handlers
}) => {
	if (tasks.length === 0) return null
	return (
		<div>
			<button
				onClick={toggleOpen}
				className="w-full flex justify-between items-center py-3 px-2 text-left hover:bg-[var(--color-primary-surface)]/50 rounded-lg transition-colors"
			>
				<h2 className="text-xl font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
					{title} ({tasks.length})
				</h2>
				<IconChevronUp
					className={cn(
						"transform transition-transform duration-200",
						!isOpen && "rotate-180"
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
						<motion.div layout className="space-y-3 pt-2 pb-4">
							{tasks.map((task) => (
								<TaskCard
									key={task.task_id}
									task={task}
									{...handlers}
								/>
							))}
						</motion.div>
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	)
}

const TaskCard = ({
	task,
	integrations,
	onViewDetails,
	onEditTask,
	onReRunTask,
	onDeleteTask,
	onApproveTask
}) => {
	const router = useRouter()
	const statusInfo = statusMap[task.status] || statusMap.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	let missingTools = []
	if (task.status === "approval_pending" && integrations) {
		const requiredTools = new Set(task.plan?.map((step) => step.tool) || [])
		requiredTools.forEach((toolName) => {
			const integration = integrations.find((i) => i.name === toolName)
			if (
				integration &&
				!integration.connected &&
				integration.auth_type !== "builtin"
			) {
				missingTools.push(integration.display_name || toolName)
			}
		})
	}

	const getScheduleText = () => {
		if (!task.schedule) return null
		const { type, run_at, frequency, time, days } = task.schedule
		if (type === "once" && run_at) {
			return `Scheduled for: ${new Date(run_at).toLocaleString()}`
		}
		if (type === "recurring") {
			let scheduleText = `Repeats ${frequency}`
			if (time) scheduleText += ` at ${time}`
			if (frequency === "weekly" && days?.length > 0) {
				scheduleText += ` on ${days.join(", ")}`
			}
			return scheduleText
		}
		return null
	}
	const scheduleText = getScheduleText()

	const renderTaskSource = () => {
		if (!task.original_context) return null
		const { source, original_content, page_date, subject, description } =
			task.original_context
		let icon, text
		switch (source) {
			case "journal_block":
				icon = <IconBook size={14} />
				text = `From Journal: "${original_content?.substring(0, 40)}..."`
				return (
					<button
						onClick={(e) => {
							e.stopPropagation()
							router.push(`/journal?date=${page_date}`)
						}}
						className="w-full text-left text-xs text-gray-500 mt-1 flex items-center gap-1.5 italic hover:text-blue-400"
						title={`Go to journal entry on ${page_date}`}
					>
						{icon}
						<span className="truncate">{text}</span>
					</button>
				)
			case "gmail":
				icon = <IconMail size={14} />
				text = `From Gmail: "${subject || "No Subject"}"`
				break
			case "gcalendar":
				icon = <IconCalendarEvent size={14} />
				text = `From Calendar: "${subject || "No Summary"}"`
				break
			case "chat":
				icon = <IconMessage size={14} />
				text = `From Chat: "${description}"`
				break
			default:
				return null
		}
		return (
			<p
				className="text-xs text-gray-500 mt-1 flex items-center gap-1.5 italic"
				title={text}
			>
				{icon}
				<span className="truncate">{text}</span>
			</p>
		)
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, y: -10 }}
			whileHover={{
				y: -2,
				boxShadow:
					"0 10px 15px -3px rgba(0, 178, 254, 0.05), 0 4px 6px -2px rgba(0, 178, 254, 0.03)"
			}}
			style={{ transformStyle: "preserve-3d" }}
			className={cn(
				"group flex items-start gap-4 bg-gradient-to-br from-[var(--color-primary-surface)] to-neutral-800/60 p-4 rounded-xl shadow-lg transition-all duration-200 border border-transparent hover:border-transparent",
				task.enabled === false
					? "border-l-4 border-gray-600 opacity-60"
					: "hover:border-blue-500/30",
				!missingTools.length && "cursor-pointer"
			)}
			onClick={(e) =>
				!e.target.closest("button, a") &&
				!missingTools.length &&
				onViewDetails(task)
			}
		>
			<div className="flex flex-col items-center w-20 flex-shrink-0 text-center">
				<statusInfo.icon className={cn("h-7 w-7", statusInfo.color)} />
				<span
					className={cn(
						"text-xs mt-1.5 font-semibold",
						priorityInfo.color
					)}
				>
					{priorityInfo.label} Priority
				</span>
			</div>
			<div className="flex-grow min-w-0">
				<div
					className={cn(
						"absolute top-2 right-2 h-2 w-2 rounded-full",
						task.enabled === false
							? "bg-gray-500"
							: statusInfo.color.replace("text-", "bg-")
					)}
				></div>
				<p className="font-semibold text-white">{task.description}</p>
				{renderTaskSource()}
				{scheduleText && (
					<p className="text-xs text-[var(--color-accent-blue)] mt-1 flex items-center gap-1.5">
						<IconRefresh size={14} />
						<span>{scheduleText}</span>
						{!task.enabled && (
							<span className="font-bold text-yellow-400">
								(Paused)
							</span>
						)}
					</p>
				)}
				{missingTools.length > 0 && (
					<div className="flex flex-wrap items-center gap-2 mt-2 text-yellow-400 text-xs">
						<div
							data-tooltip-id={`missing-tools-tooltip-${task.task_id}`}
							data-tooltip-content="Please connect these tools in Settings to approve this task."
							className="flex items-center gap-2"
						>
							<IconAlertTriangle size={14} />
							<span>Requires: {missingTools.join(", ")}</span>
						</div>
						<ConnectToolButton toolName={missingTools[0]} />
						<Tooltip
							id={`missing-tools-tooltip-${task.task_id}`}
							place="bottom"
						/>
					</div>
				)}
			</div>
			<div className="flex flex-col items-end gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
				{onApproveTask && (
					<button
						onClick={(e) => {
							e.stopPropagation()
							onApproveTask(task.task_id)
						}}
						className="p-1.5 rounded-md text-[var(--color-accent-green)] hover:bg-[var(--color-primary-surface-elevated)] disabled:text-gray-600 disabled:cursor-not-allowed"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Approve this plan for execution"
						disabled={missingTools.length > 0}
					>
						<IconCircleCheck className="h-5 w-5" />
					</button>
				)}
				{onEditTask && (
					<button
						onClick={(e) => {
							e.stopPropagation()
							onEditTask(task)
						}}
						className="p-1.5 rounded-md text-[var(--color-accent-orange)] hover:bg-[var(--color-primary-surface-elevated)]"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Edit this task's plan and properties"
					>
						<IconPencil className="h-5 w-5" />
					</button>
				)}
				{onReRunTask && (
					<button
						onClick={(e) => {
							e.stopPropagation()
							onReRunTask(task.task_id)
						}}
						className="p-1.5 rounded-md text-[var(--color-accent-blue)] hover:bg-[var(--color-primary-surface-elevated)]"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Create a new copy of this task to run again"
					>
						<IconRefresh className="h-5 w-5" />
					</button>
				)}
				{onDeleteTask && (
					<button
						onClick={(e) => {
							e.stopPropagation()
							onDeleteTask(task.task_id)
						}}
						className="p-1.5 rounded-md text-[var(--color-accent-red)] hover:bg-[var(--color-primary-surface-elevated)]"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Delete this task permanently"
					>
						<IconTrash className="h-5 w-5" />
					</button>
				)}
			</div>
		</motion.div>
	)
}

const TaskDetailsModal = ({ task, onClose, onApprove, integrations }) => {
	const statusInfo = statusMap[task.status] || statusMap.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default
	let missingTools = []
	if (task.status === "approval_pending" && integrations) {
		const requiredTools = new Set(task.plan?.map((step) => step.tool) || [])
		requiredTools.forEach((toolName) => {
			if (
				!integrations.find((i) => i.name === toolName)?.connected &&
				integrations.find((i) => i.name === toolName)?.auth_type !==
					"builtin"
			) {
				missingTools.push(
					integrations.find((i) => i.name === toolName)
						?.display_name || toolName
				)
			}
		})
	}
	const { thoughts, finalAnswer, mainContent } =
		task.result && typeof task.result === "string"
			? {
					thoughts: task.result.match(
						/<think>([\s\S]*?)<\/think>/
					)?.[1],
					finalAnswer: task.result.match(
						/<final_answer>([\s\S]*?)<\/final_answer>/
					)?.[1],
					mainContent: task.result
						.replace(/<think>[\s\S]*?<\/think>/g, "")
						.replace(/<final_answer>[\s\S]*?<\/final_answer>/g, "")
				}
			: { thoughts: null, finalAnswer: null, mainContent: task.result }

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
							Status:
						</span>
						<span
							className={cn(
								"font-semibold py-0.5 px-2 rounded-full text-xs",
								statusInfo.color,
								statusInfo.borderColor.replace(
									"border-",
									"bg-"
								) + "/20"
							)}
						>
							{statusInfo.label}
						</span>
						<div className="w-px h-4 bg-[var(--color-primary-surface-elevated)]"></div>
						<span className="text-[var(--color-text-secondary)]">
							Priority:
						</span>
						<span
							className={cn("font-semibold", priorityInfo.color)}
						>
							{priorityInfo.label}
						</span>
					</div>
					<div>
						<h4 className="text-lg font-semibold text-white mb-3">
							Plan
						</h4>
						<div className="space-y-2">
							{task.plan.map((step, index) => (
								<div
									key={index}
									className="flex items-start gap-3 bg-[var(--color-primary-surface)]/70 p-3 rounded-md"
								>
									<div className="flex-shrink-0 text-[var(--color-accent-blue)] font-bold mt-0.5">
										{index + 1}.
									</div>
									<div>
										<p className="font-semibold text-white">
											{step.tool}
										</p>
										<p className="text-sm text-[var(--color-text-secondary)]">
											{step.description}
										</p>
									</div>
								</div>
							))}
						</div>
					</div>
					{task.progress_updates?.length > 0 && (
						<div>
							<h4 className="text-lg font-semibold text-white mb-4">
								Progress
							</h4>
							<div className="space-y-4">
								{task.progress_updates.map((update, index) => (
									<div key={index} className="flex gap-4">
										<div className="flex flex-col items-center">
											<div className="w-4 h-4 bg-blue-500 rounded-full border-2 border-neutral-800"></div>
											{index <
												task.progress_updates.length -
													1 && (
												<div className="w-0.5 flex-grow bg-[var(--color-primary-surface-elevated)]"></div>
											)}
										</div>
										<div>
											<p className="text-sm text-white -mt-1">
												{update.message}
											</p>
											<p className="text-xs text-[var(--color-text-muted)] mt-1.5">
												{new Date(
													update.timestamp
												).toLocaleString()}
											</p>
										</div>
									</div>
								))}
							</div>
						</div>
					)}
					{(task.result || task.error) && (
						<div className="pt-4 border-t border-[var(--color-primary-surface-elevated)]">
							<h4 className="text-lg font-semibold text-white mb-4">
								Outcome
							</h4>
							{task.error ? (
								<pre className="text-sm bg-red-900/30 p-4 rounded-md text-red-300 whitespace-pre-wrap font-mono border border-[var(--color-accent-red)]/50">
									{task.error}
								</pre>
							) : (
								<div className="space-y-4 text-gray-300">
									{thoughts && (
										<details className="bg-[var(--color-primary-surface)]/50 rounded-lg p-3 border border-[var(--color-primary-surface-elevated)]">
											<summary
												className="cursor-pointer text-sm text-[var(--color-text-secondary)] font-semibold hover:text-white flex items-center gap-2"
												data-tooltip-id="task-details-tooltip"
												data-tooltip-content="See the step-by-step reasoning the agent used to produce the result."
											>
												<IconBrain
													size={16}
													className="text-yellow-400"
												/>{" "}
												View Agent's Thoughts
											</summary>
											<pre className="mt-3 text-xs text-gray-400 whitespace-pre-wrap font-mono">
												{thoughts}
											</pre>
										</details>
									)}
									{mainContent &&
										typeof mainContent === "string" && (
											<div
												dangerouslySetInnerHTML={{
													__html: mainContent.replace(
														/\n/g,
														"<br />"
													)
												}}
											/>
										)}
									{finalAnswer && (
										<div className="mt-2 p-4 bg-green-900/30 border border-[var(--color-accent-green)]/50 rounded-lg">
											<p className="text-sm font-semibold text-green-300 mb-2">
												Final Answer
											</p>
											<div
												dangerouslySetInnerHTML={{
													__html: finalAnswer.replace(
														/\n/g,
														"<br />"
													)
												}}
											/>
										</div>
									)}
								</div>
							)}
						</div>
					)}
				</div>
				<div className="flex justify-end mt-6 pt-4 border-t border-[var(--color-primary-surface-elevated)] gap-4">
					<button
						onClick={onClose}
						className="py-2.5 px-6 rounded-lg bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-sm transition-colors"
					>
						Close
					</button>
					{task.status === "approval_pending" && (
						<button
							onClick={() => onApprove(task.task_id)}
							className="py-2.5 px-6 rounded-lg bg-[var(--color-accent-green)] hover:bg-[var(--color-accent-green-hover)] text-sm flex items-center gap-2 disabled:opacity-50 transition-colors"
							disabled={missingTools.length > 0}
						>
							<IconCircleCheck className="w-5 h-5" />
							Approve Plan
						</button>
					)}
				</div>
			</motion.div>
		</motion.div>
	)
}

const ScheduleEditor = ({ schedule, setSchedule }) => {
	const handleTypeChange = (type) => {
		const baseSchedule = { ...schedule, type }
		if (type === "once") {
			delete baseSchedule.frequency // This is fine
			delete baseSchedule.days
			delete baseSchedule.time
		} else {
			delete baseSchedule.run_at // This is fine
		}
		setSchedule(baseSchedule)
	}

	const handleDayToggle = (day) => {
		const currentDays = schedule.days || []
		const newDays = currentDays.includes(day)
			? currentDays.filter((d) => d !== day)
			: [...currentDays, day]
		setSchedule({ ...schedule, days: newDays })
	}

	return (
		<div className="bg-neutral-800/50 p-4 rounded-lg space-y-4 border border-neutral-700/80">
			<div className="flex items-center gap-2">
				{[
					{ label: "Run Once", value: "once" },
					{ label: "Recurring", value: "recurring" }
				].map(({ label, value }) => (
					<button
						key={value}
						onClick={() => handleTypeChange(value)}
						className={cn(
							"px-4 py-1.5 rounded-full text-sm",
							(schedule.type || "once") === value
								? "bg-[var(--color-accent-blue)] text-white"
								: "bg-neutral-600 hover:bg-neutral-500"
						)}
					>
						{label}
					</button>
				))}
			</div>

			{(schedule.type === "once" || !schedule.type) && (
				<div>
					<label className="text-xs text-gray-400 block mb-1">
						Run At (optional, local time)
					</label>
					<input
						type="datetime-local"
						value={schedule.run_at || ""}
						onChange={(e) =>
							setSchedule({ ...schedule, run_at: e.target.value })
						}
						className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
					/>
					<p className="text-xs text-gray-500 mt-1">
						If left blank, the task will run immediately after
						approval.
					</p>
				</div>
			)}

			{schedule.type === "recurring" && (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label className="text-xs text-gray-400 block mb-1">
							Frequency
						</label>
						<select
							value={schedule.frequency || "daily"}
							onChange={(e) =>
								setSchedule({
									...schedule,
									frequency: e.target.value
								})
							}
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
						>
							<option value="daily">Daily</option>
							<option value="weekly">Weekly</option>
						</select>
					</div>
					<div>
						<label
							className="text-xs text-gray-400 block mb-1"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Tasks are scheduled in Coordinated Universal Time (UTC) to ensure consistency across timezones."
						>
							Time (UTC)
						</label>
						<input
							type="time"
							value={schedule.time || "09:00"}
							onChange={(e) =>
								setSchedule({
									...schedule,
									time: e.target.value
								})
							}
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
						/>
					</div>
					{schedule.frequency === "weekly" && (
						<div className="md:col-span-2">
							<label className="text-xs text-gray-400 block mb-2">
								Days
							</label>
							<div className="flex flex-wrap gap-2">
								{[
									"Monday",
									"Tuesday",
									"Wednesday",
									"Thursday",
									"Friday",
									"Saturday",
									"Sunday"
								].map((day) => (
									<button
										key={day}
										onClick={() => handleDayToggle(day)}
										className={cn(
											"px-3 py-1.5 rounded-full text-xs font-semibold",
											(schedule.days || []).includes(day)
												? "bg-[var(--color-accent-blue)] text-white"
												: "bg-neutral-600 hover:bg-neutral-500"
										)}
									>
										{day.substring(0, 3)}
									</button>
								))}
							</div>
						</div>
					)}
				</div>
			)}
		</div>
	)
}

export default Tasks
