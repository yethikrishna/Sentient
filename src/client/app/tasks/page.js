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
	IconMenu2,
	IconGripVertical,
	IconBrain,
	IconBook,
	IconMail,
	IconCalendarEvent,
	IconMessage,
	IconArrowRight
} from "@tabler/icons-react"
import Sidebar from "@components/Sidebar"
import toast from "react-hot-toast"
import { Tooltip } from "react-tooltip"
import "react-tooltip/dist/react-tooltip.css"
import { cn } from "@utils/cn"
import { useSmoothScroll } from "@hooks/useSmoothScroll"
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
	const [userDetails, setUserDetails] = useState({})
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [editingTask, setEditingTask] = useState(null)
	const [filterStatus, setFilterStatus] = useState("all")
	const [isGeneratingPlan, setIsGeneratingPlan] = useState(false)
	const [searchTerm, setSearchTerm] = useState("")
	const [viewingTask, setViewingTask] = useState(null)
	const [isCreatePlanOpen, setCreatePlanOpen] = useState(false)
	const [createStep, setCreateStep] = useState("generate") // 'generate' or 'review'
	const [openSections, setOpenSections] = useState({
		active: true,
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
		frequency: "daily",
		time: "09:00",
		days: []
	})
	const [allTools, setAllTools] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [loadingIntegrations, setLoadingIntegrations] = useState(true)
	const scrollRef = useRef(null)

	useSmoothScroll(scrollRef)

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

	const fetchUserDetails = async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user profile")
			setUserDetails(await response.json())
		} catch (error) {
			toast.error("Error fetching user details for sidebar.")
		}
	}

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
		fetchUserDetails()
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

	const handleAddTask = async () => {
		if (!newTaskDescription.trim())
			return toast.error("Please enter a task description.")
		if (newTaskPlan.some((step) => !step.tool || !step.description.trim()))
			return toast.error(
				"All plan steps must have a tool and description."
			)
		setIsAdding(true)
		try {
			const taskData = {
				description: newTaskDescription,
				priority: newTaskPriority,
				plan: newTaskPlan,
				schedule: newSchedule.type === "once" ? null : newSchedule
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
			const response = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					taskId: editingTask.task_id,
					description: editingTask.description,
					priority: editingTask.priority,
					plan: editingTask.plan,
					schedule: editingTask.schedule
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
		<div className="h-screen bg-[var(--color-primary-background)] flex relative overflow-hidden dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col h-full bg-[var(--color-primary-background)] text-white relative overflow-hidden">
				<header className="flex items-center justify-between p-4 bg-[var(--color-primary-background)] border-b border-neutral-800 md:hidden">
					<button onClick={() => setSidebarVisible(true)}>
						<IconMenu2 />
					</button>
				</header>
				<div className="flex-shrink-0 p-4 pt-6 flex justify-center z-30">
					<div className="w-full max-w-3xl flex items-center space-x-3 bg-neutral-800/80 backdrop-blur-sm rounded-full p-2 shadow-lg border border-neutral-700">
						<IconSearch className="h-6 w-6 text-gray-400 ml-2 flex-shrink-0" />
						<input
							type="text"
							placeholder="Search tasks by description..."
							value={searchTerm}
							onChange={(e) => setSearchTerm(e.target.value)}
							className="bg-transparent text-white focus:outline-none w-full px-2 text-base"
						/>
						<div className="relative flex-shrink-0">
							<select
								value={filterStatus}
								onChange={(e) =>
									setFilterStatus(e.target.value)
								}
								className="appearance-none bg-neutral-700 border border-neutral-600 text-white text-sm rounded-full pl-4 pr-8 py-2 focus:outline-none focus:border-lightblue cursor-pointer"
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
							className="p-2 rounded-full hover:bg-neutral-700 transition-colors text-gray-300"
							disabled={loading && tasks.length > 0}
						>
							{loading && tasks.length > 0 ? (
								<IconLoader className="h-6 w-6 animate-spin" />
							) : (
								<IconRefresh className="h-6 w-6" />
							)}
						</button>
					</div>
				</div>

				<main
					ref={scrollRef}
					className="flex-1 w-full max-w-3xl mx-auto flex flex-col overflow-hidden px-4"
				>
					<div className="flex-grow overflow-y-auto space-y-2 no-scrollbar pb-36">
						{loading || loadingIntegrations ? (
							<div className="flex justify-center items-center h-full">
								<IconLoader className="w-10 h-10 animate-spin" />
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

				<div className="absolute bottom-0 left-0 right-0 p-4 bg-[#1a1a1a]/80 backdrop-blur-sm border-t border-[#2a2a2a] z-40">
					<div className="max-w-3xl mx-auto">
						<div
							onClick={() => setCreatePlanOpen(!isCreatePlanOpen)}
							className="flex justify-between items-center cursor-pointer"
						>
							<h3 className="text-lg font-semibold text-white">
								Create a New Plan
							</h3>
							<IconChevronUp
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
												className="w-full p-3 bg-[#2a2a2a] border border-[#3a3a3a] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#4a9eff]"
											/>
											<div className="flex justify-end">
												<button
													onClick={handleGeneratePlan}
													disabled={isGeneratingPlan}
													className="p-3 px-6 bg-[#4a9eff] hover:bg-blue-500 rounded-lg text-white font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
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
													className="py-2.5 px-6 rounded-lg bg-neutral-600 hover:bg-neutral-500 text-white text-sm font-semibold"
												>
													Back
												</button>
												<button
													onClick={handleAddTask}
													disabled={isAdding}
													className="py-2.5 px-6 rounded-lg bg-[#4a9eff] hover:bg-blue-500 text-white text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
												>
													{isAdding && (
														<IconLoader className="h-5 w-5 animate-spin" />
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
						allTools={allTools}
						integrations={integrations}
					/>
				)}
			</div>
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
						className="md:col-span-2 p-3 bg-[#2a2a2a] border border-[#3a3a3a] rounded-lg"
					/>
					<select
						value={priority}
						onChange={(e) => setPriority(Number(e.target.value))}
						className="p-3 bg-[#2a2a2a] border border-[#3a3a3a] rounded-lg appearance-none"
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
							className="flex items-center gap-3"
						>
							<IconGripVertical className="h-5 w-5 text-gray-500 flex-shrink-0" />
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
										className="w-2/5 p-2 bg-[#2a2a2a] border border-[#3a3a3a] rounded-md text-sm"
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
										className="flex-grow p-2 bg-[#2a2a2a] border border-[#3a3a3a] rounded-md text-sm"
									/>
									<button
										onClick={() => handleRemoveStep(index)}
										className="p-2 text-red-400 hover:bg-neutral-700 rounded-full"
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
					className="flex items-center gap-1.5 py-1.5 px-3 rounded-full bg-[#3a3a3a] hover:bg-[#4a4a4a] text-xs"
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
	allTools,
	integrations
}) => {
	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<div className="bg-neutral-800 p-8 rounded-lg shadow-xl w-full max-w-3xl mx-auto max-h-[90vh] flex flex-col">
				<div className="flex justify-between items-center mb-6">
					<h3 className="text-xl font-semibold">Edit Task</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-4 space-y-6">
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
						schedule={task.schedule || { type: "once" }}
						setSchedule={(val) =>
							setTask({ ...task, schedule: val })
						}
						allTools={allTools}
						integrations={integrations}
					/>
				</div>
				<div className="flex justify-end gap-4 mt-6 pt-4 border-t border-neutral-700">
					<button
						onClick={onClose}
						className="py-2.5 px-5 rounded bg-neutral-600 hover:bg-neutral-500 text-sm"
					>
						Cancel
					</button>
					<button
						onClick={onSave}
						className="py-2.5 px-5 rounded bg-green-600 hover:bg-green-500 text-sm"
					>
						Save Changes
					</button>
				</div>
			</div>
		</motion.div>
	)
}

const ConnectToolButton = ({ toolName }) => {
	const router = useRouter()
	return (
		<button
			onClick={() => router.push(`/settings?connect=${toolName}`)}
			className="text-xs self-start bg-yellow-600/80 text-white font-semibold py-1 px-3 rounded-md hover:bg-yellow-500 transition-colors whitespace-nowrap"
		>
			Connect {toolName} in Settings
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
				className="w-full flex justify-between items-center py-3 px-2 text-left"
			>
				<h2 className="text-xl font-semibold text-gray-300 flex items-center gap-2">
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
						<div className="space-y-3 pt-2 pb-4">
							{tasks.map((task) => (
								<TaskCard
									key={task.task_id}
									task={task}
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

	const scheduleText = task.schedule
		? `Repeats ${task.schedule.frequency}`
		: null

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
			className={cn(
				"group flex items-start gap-4 bg-neutral-800 p-4 rounded-lg shadow-md hover:bg-neutral-700/60 transition-colors duration-150 border-l-4",
				task.enabled === false
					? "border-gray-600 opacity-60"
					: statusInfo.borderColor,
				!missingTools.length && "cursor-pointer"
			)}
			onClick={() => !missingTools.length && onViewDetails(task)}
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
				<p className="font-semibold text-white">{task.description}</p>
				{renderTaskSource()}
				{scheduleText && (
					<p className="text-xs text-blue-400 mt-1 flex items-center gap-1.5">
						<IconRefresh size={14} />
						<span>{scheduleText}</span>
						{!task.enabled && (
							<span className="font-bold text-yellow-400">
								(Disabled)
							</span>
						)}
					</p>
				)}
				{missingTools.length > 0 && (
					<div className="flex items-center gap-2 mt-2 text-yellow-400 text-xs">
						<IconAlertTriangle size={14} />
						<span>Requires: {missingTools.join(", ")}</span>
						<Tooltip
							id={`missing-tools-tooltip-${task.task_id}`}
							content="Please connect these tools in Settings to approve this task."
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
						className="p-1.5 rounded-md text-green-400 hover:bg-neutral-900/50 disabled:text-gray-600 disabled:cursor-not-allowed"
						title="Approve Plan"
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
						className="p-1.5 rounded-md text-yellow-400 hover:bg-neutral-900/50"
						title="Edit"
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
						className="p-1.5 rounded-md text-blue-400 hover:bg-neutral-900/50"
						title="Re-run Task"
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
						className="p-1.5 rounded-md text-red-400 hover:bg-neutral-900/50"
						title="Delete"
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
			<div className="bg-neutral-800 p-8 rounded-lg shadow-xl w-full max-w-3xl mx-auto max-h-[90vh] flex flex-col">
				<div className="flex justify-between items-center mb-6">
					<h3 className="text-2xl font-semibold text-white truncate">
						{task.description}
					</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-4 space-y-8">
					<div className="flex items-center gap-4 text-sm">
						<span className="text-gray-400">Status:</span>
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
						<div className="w-px h-4 bg-neutral-600"></div>
						<span className="text-gray-400">Priority:</span>
						<span
							className={cn("font-semibold", priorityInfo.color)}
						>
							{priorityInfo.label}
						</span>
					</div>
					<div>
						<h4 className="text-lg font-semibold text-gray-300 mb-3">
							Plan
						</h4>
						<div className="space-y-2">
							{task.plan.map((step, index) => (
								<div
									key={index}
									className="flex items-start gap-3 bg-neutral-700/50 p-3 rounded-md"
								>
									<div className="flex-shrink-0 text-blue-400 font-bold mt-0.5">
										{index + 1}.
									</div>
									<div>
										<p className="font-semibold text-gray-200">
											{step.tool}
										</p>
										<p className="text-sm text-gray-400">
											{step.description}
										</p>
									</div>
								</div>
							))}
						</div>
					</div>
					{task.progress_updates?.length > 0 && (
						<div>
							<h4 className="text-lg font-semibold text-gray-300 mb-4">
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
												<div className="w-0.5 flex-grow bg-neutral-700"></div>
											)}
										</div>
										<div>
											<p className="text-sm text-gray-300 -mt-1">
												{update.message}
											</p>
											<p className="text-xs text-gray-500 mt-1.5">
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
						<div className="pt-4 border-t border-neutral-700/50">
							<h4 className="text-lg font-semibold text-gray-200 mb-4">
								Outcome
							</h4>
							{task.error ? (
								<pre className="text-sm bg-red-900/30 p-4 rounded-md text-red-300 whitespace-pre-wrap font-mono border border-red-500/50">
									{task.error}
								</pre>
							) : (
								<div className="space-y-4 text-gray-300">
									{thoughts && (
										<details className="bg-neutral-900/50 rounded-lg p-3 border border-neutral-700">
											<summary className="cursor-pointer text-sm text-gray-400 font-semibold hover:text-white flex items-center gap-2">
												<IconBrain size={16} /> View
												Agent's Thoughts
											</summary>
											<pre className="mt-3 text-xs text-gray-400 whitespace-pre-wrap font-mono">
												{thoughts}
											</pre>
										</details>
									)}
									{mainContent && (
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
										<div className="mt-2 p-4 bg-green-900/30 border border-green-500/50 rounded-lg">
											<p className="text-sm font-semibold text-green-300 mb-1">
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
				<div className="flex justify-end mt-6 pt-4 border-t border-neutral-700 gap-4">
					<button
						onClick={onClose}
						className="py-2.5 px-6 rounded bg-neutral-600 hover:bg-neutral-500 text-sm"
					>
						Close
					</button>
					{task.status === "approval_pending" && (
						<button
							onClick={() => onApprove(task.task_id)}
							className="py-2.5 px-6 rounded bg-green-600 hover:bg-green-500 text-sm flex items-center gap-2 disabled:opacity-50"
							disabled={missingTools.length > 0}
						>
							<IconCircleCheck className="w-5 h-5" />
							Approve Plan
						</button>
					)}
				</div>
			</div>
		</motion.div>
	)
}

const ScheduleEditor = ({ schedule, setSchedule }) => {
	const handleDayToggle = (day) => {
		const currentDays = schedule.days || []
		const newDays = currentDays.includes(day)
			? currentDays.filter((d) => d !== day)
			: [...currentDays, day]
		setSchedule({ ...schedule, days: newDays })
	}
	return (
		<div className="bg-neutral-700/50 p-4 rounded-lg space-y-4">
			<div className="flex items-center gap-2">
				{[
					{ label: "Run Once", value: "once" },
					{ label: "Recurring", value: "recurring" }
				].map(({ label, value }) => (
					<button
						key={value}
						onClick={() =>
							setSchedule({ ...schedule, type: value })
						}
						className={cn(
							"px-4 py-1.5 rounded-full text-sm",
							schedule.type === value
								? "bg-lightblue text-white"
								: "bg-neutral-600 hover:bg-neutral-500"
						)}
					>
						{label}
					</button>
				))}
			</div>
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
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md"
						>
							<option value="daily">Daily</option>
							<option value="weekly">Weekly</option>
						</select>
					</div>
					<div>
						<label className="text-xs text-gray-400 block mb-1">
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
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md"
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
												? "bg-lightblue text-white"
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
