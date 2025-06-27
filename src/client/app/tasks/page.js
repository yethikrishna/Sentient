"use client"

import React, { useState, useEffect, useCallback } from "react"
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
	IconMessage
} from "@tabler/icons-react"
import ReactMarkdown from "react-markdown"
import Sidebar from "@components/Sidebar"
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
		// New status for recurring tasks
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
	const [viewingTask, setViewingTask] = useState(null) // For viewing task details/approval
	const [isCreatePlanOpen, setCreatePlanOpen] = useState(true)
	const [openSections, setOpenSections] = useState({
		active: true,
		approval_pending: true,
		processing: true,
		completed: true
	})
	const [isAdding, setIsAdding] = useState(false)
	const [generationPrompt, setGenerationPrompt] = useState("")
	const [newTaskDescription, setNewTaskDescription] = useState("") // Populated by AI or manual edit
	const [newTaskPriority, setNewTaskPriority] = useState(1)
	const [newTaskPlan, setNewTaskPlan] = useState([
		{ tool: "", description: "" }
	])
	const [newSchedule, setNewSchedule] = useState({
		type: "once",
		frequency: "daily",
		time: "09:00",
		days: []
	})
	const [availableTools, setAvailableTools] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [loadingIntegrations, setLoadingIntegrations] = useState(true)

	// --- Fetching Data ---
	const fetchTasksData = useCallback(async () => {
		console.log("Fetching tasks data...")
		// The loading state is managed by the initial state and the finally block,
		// so we don't need to check tasks.length here. This makes the function stable.
		setError(null)
		try {
			const response = await fetch("/api/tasks")
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to fetch tasks")
			}
			if (Array.isArray(data.tasks)) {
				const sortedTasks = data.tasks.sort((a, b) => {
					const statusOrder = {
						active: -2,
						approval_pending: -1, // Highest priority
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
						console.warn("Error comparing task dates:", dateError)
						return 0
					}
				})
				setTasks(sortedTasks)
				console.log("Tasks fetched and sorted:", sortedTasks.length)
			} else {
				throw new Error("Invalid tasks response format")
			}
		} catch (err) {
			console.error("Exception fetching tasks:", err)
			setError("Failed to fetch tasks: " + err.message)
			setTasks([])
		} finally {
			console.log("Finished fetching tasks, setting loading false.")
			setLoading(false)
		}
	}, []) // Empty dependency array makes this function stable

	const fetchUserDetails = async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user profile")
			const data = await response.json()
			setUserDetails(data || {})
		} catch (error) {
			toast.error("Error fetching user details for sidebar.")
			console.error("Error fetching user details for sidebar:", error)
		}
	}

	const fetchIntegrations = async () => {
		setLoadingIntegrations(true)
		try {
			const response = await fetch("/api/settings/integrations")
			if (!response.ok)
				throw new Error("Failed to fetch integrations status")
			const data = await response.json()
			setIntegrations(data.integrations || [])
		} catch (error) {
			toast.error(error.message)
			setIntegrations([])
		} finally {
			setLoadingIntegrations(false)
		}
	}

	const fetchAvailableTools = async () => {
		try {
			const response = await fetch("/api/settings/integrations")
			if (!response.ok) throw new Error("Failed to fetch available tools")
			const data = await response.json()
			const integrations = data.integrations || []

			const googleAuthResponse = await fetch("/api/settings/google-auth")
			const googleAuthData = await googleAuthResponse.json()
			const googleAuthMode = googleAuthData.mode || "default"

			const tools = integrations
				.filter((i) => {
					// Built-in tools are always available.
					if (i.auth_type === "builtin") {
						return true
					}
					// For Google-specific OAuth tools, check connection status or if custom mode is on.
					const isGoogleTool = i.name.startsWith("g")
					if (isGoogleTool) {
						return googleAuthMode === "custom" || i.connected
					}
					// For other OAuth/manual tools (like Slack, Notion, GitHub), just check connection status.
					return i.connected
				})
				.map((i) => ({ name: i.name, display_name: i.display_name }))

			setAvailableTools(tools)
		} catch (err) {
			toast.error(err.message)
			setAvailableTools([])
		}
	}

	useEffect(() => {
		fetchUserDetails()
		fetchTasksData()
		fetchIntegrations()
		fetchAvailableTools()
		const intervalId = setInterval(fetchTasksData, 60000)
		return () => clearInterval(intervalId)
	}, [fetchTasksData])

	// --- Task Actions ---
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
			if (!response.ok) {
				throw new Error(data.detail || "Failed to generate plan.")
			}
			if (!data.plan || data.plan.length === 0) {
				toast.error(
					"The agent could not generate a plan for this goal. Please try rephrasing."
				)
			} else {
				setNewTaskDescription(data.description || generationPrompt)
				setNewTaskPlan(data.plan)
				toast.success("Plan generated! Review and save it below.")
			}
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsGeneratingPlan(false)
		}
	}

	const handleAddTask = async () => {
		if (!newTaskDescription.trim()) {
			toast.error("Please enter a task description.")
			return
		}
		if (
			newTaskPlan.some((step) => !step.tool || !step.description.trim())
		) {
			toast.error("All plan steps must have a tool and description.")
			return
		}
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
			setNewTaskDescription("")
			setNewTaskPriority(1)
			setNewTaskPlan([{ tool: "", description: "" }])
			setNewSchedule({
				type: "once",
				frequency: "daily",
				time: "09:00",
				days: []
			})
			setNewTaskPlan([{ tool: "", description: "" }])
			await fetchTasksData()
		} catch (error) {
			console.error("Exception adding task:", error)
			toast.error(`Failed to add task: ${error.message}`)
		} finally {
			setIsAdding(false)
		}
	}

	const handleAddStep = () => {
		setNewTaskPlan([...newTaskPlan, { tool: "", description: "" }])
	}

	const handleRemoveStep = (index) => {
		const newPlan = newTaskPlan.filter((_, i) => i !== index)
		setNewTaskPlan(newPlan)
	}

	const handleStepChange = (index, field, value) => {
		const newPlan = [...newTaskPlan]
		newPlan[index][field] = value
		setNewTaskPlan(newPlan)
	}

	const handleEditStepChange = (index, field, value) => {
		setEditingTask((prev) => {
			const newPlan = [...prev.plan]
			newPlan[index][field] = value
			return { ...prev, plan: newPlan }
		})
	}

	const handleAddStepToEditModal = () => {
		setEditingTask((prev) => ({
			...prev,
			plan: [...prev.plan, { tool: "", description: "" }]
		}))
	}

	const handleRemoveStepFromEditModal = (index) => {
		setEditingTask((prev) => ({
			...prev,
			plan: prev.plan.filter((_, i) => i !== index)
		}))
	}

	const handleEditTask = (task) => {
		console.log("Editing task:", task)
		setEditingTask({ ...task })
	}

	const handleUpdateTask = async () => {
		if (!editingTask || !editingTask.description?.trim()) {
			toast.error("Task description cannot be empty.")
			return
		}
		if (
			editingTask.priority === undefined ||
			editingTask.priority === null ||
			![0, 1, 2].includes(editingTask.priority)
		) {
			toast.error("Invalid priority selected.")
			return
		}
		if (
			editingTask.plan.some(
				(step) => !step.tool || !step.description?.trim()
			)
		) {
			toast.error("All plan steps must have a tool and description.")
			return
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
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to update task")
			}
			toast.success("Task updated successfully!")
			setEditingTask(null)
			await fetchTasksData()
		} catch (error) {
			console.error("Exception updating task:", error)
			toast.error(`Failed to update task: ${error.message}`)
		}
	}

	const handleDeleteTask = async (taskId) => {
		if (!taskId) return
		if (!window.confirm("Are you sure you want to delete this task?"))
			return
		console.log("Deleting task:", taskId)
		try {
			const response = await fetch("/api/tasks/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})

			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "Failed to delete task")
			}
			toast.success("Task deleted successfully!")
			setViewingTask(null) // Close modal if deleted task was being viewed
			await fetchTasksData()
		} catch (error) {
			console.error("Exception deleting task:", error)
			toast.error(`Failed to delete task: ${error.message}`)
		}
	}

	const handleApproveTask = async (taskId) => {
		if (!taskId) return
		console.log("Approving task:", taskId)
		try {
			// Optimistically update the UI
			setTasks((prevTasks) =>
				prevTasks.map((t) =>
					t.task_id === taskId ? { ...t, status: "pending" } : t
				)
			)
			if (viewingTask?.task_id === taskId) {
				setViewingTask((prev) => ({ ...prev, status: "pending" }))
			}

			const response = await fetch("/api/tasks/approve", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) {
				const errorData = await response.json()
				// Handle the new specific error for missing integrations
				if (response.status === 409) {
					toast.error(errorData.detail, {
						duration: 6000,
						icon: <IconAlertTriangle className="text-yellow-400" />
					})
				} else {
					throw new Error(errorData.error || "Approval failed")
				}
				// Revert optimistic UI update because approval failed
				fetchTasksData()
				return // Stop execution
			}
			toast.success("Plan approved! Task has been queued for execution.")
			setEditingTask(null) // Close any open modals
			setViewingTask(null)
			await fetchTasksData()
		} catch (error) {
			console.error("Exception approving task:", error)
			toast.error(`Error approving task: ${error.message}`)
			fetchTasksData() // Re-fetch to revert optimistic update on error
		}
	}

	const handleReRunTask = async (taskId) => {
		if (!taskId) return
		if (
			!window.confirm(
				"Are you sure you want to create a new copy of this task to run again?"
			)
		)
			return

		try {
			const response = await fetch("/api/tasks/rerun", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to re-run task.")
			}
			toast.success("Task duplicated and is now pending approval.")
			await fetchTasksData()
		} catch (error) {
			toast.error(`Failed to re-run task: ${error.message}`)
		}
	}

	// --- Filtering Logic ---
	const filteredTasks = tasks.filter((task) => {
		if (filterStatus !== "all" && task.status !== filterStatus) return false
		if (
			searchTerm &&
			!task.description?.toLowerCase().includes(searchTerm.toLowerCase())
		)
			return false
		return true
	})
	const activeTasks = filteredTasks.filter((t) => t.status === "active")

	const pendingApprovalTasks = filteredTasks.filter(
		(t) => t.status === "approval_pending"
	)
	const processingTasks = filteredTasks.filter((t) =>
		["processing", "pending"].includes(t.status)
	)
	const completedTasks = filteredTasks.filter((t) =>
		["completed", "error", "cancelled"].includes(t.status)
	)

	const toggleSection = (section) => {
		setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }))
	}

	// --- Render Loading/Error States ---
	if (loading && tasks.length === 0) {
		// Show loader only on initial load
		return (
			<div className="flex justify-center items-center h-screen bg-matteblack">
				<IconLoader className="w-10 h-10 animate-spin text-white" />
				<span className="ml-2 text-white">Loading tasks...</span>
			</div>
		)
	}
	if (error && tasks.length === 0) {
		// Show error only if there are no tasks to display
		return (
			<div className="flex flex-col justify-center items-center h-screen bg-matteblack text-red-500">
				<p>Error loading tasks: {error}</p>
				<button
					onClick={fetchTasksData}
					className="mt-4 py-2 px-4 bg-lightblue text-white rounded hover:bg-blue-700"
				>
					Retry
				</button>
			</div>
		)
	}

	// --- Main Render ---
	return (
		<div className="h-screen bg-matteblack flex relative overflow-hidden dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col h-full bg-matteblack text-white relative overflow-hidden">
				<header className="flex items-center justify-between p-4 bg-matteblack border-b border-neutral-800 md:hidden">
					<button
						onClick={() => setSidebarVisible(true)}
						className="text-white"
					>
						<IconMenu2 />
					</button>
					<h1 className="text-lg font-semibold text-white">Today</h1>
				</header>
				{/* --- Top Bar for Search/Filter --- */}
				<div className="md:absolute md:top-6 md:left-1/2 md:transform md:-translate-x-1/2 z-30 w-full max-w-3xl md:px-4 p-4 md:p-0">
					<div className="flex items-center space-x-3 bg-neutral-800/80 backdrop-blur-sm rounded-full p-3 shadow-lg border border-neutral-700">
						<IconSearch className="h-6 w-6 text-gray-400 ml-2 flex-shrink-0" />
						<input
							type="text"
							placeholder="Search tasks..."
							value={searchTerm}
							onChange={(e) => setSearchTerm(e.target.value)}
							className="bg-transparent text-white focus:outline-none w-full flex-grow px-2 placeholder-gray-500 text-base rounded-md py-1"
						/>
						<div className="relative flex-shrink-0">
							<IconFilter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
							<select
								value={filterStatus}
								onChange={(e) =>
									setFilterStatus(e.target.value)
								}
								className="appearance-none bg-neutral-700 border border-neutral-600 text-white text-sm rounded-full pl-9 pr-4 py-2 focus:outline-none focus:border-lightblue cursor-pointer"
								title="Filter tasks by status"
							>
								<option value="all">All</option>
								<option value="pending">Pending</option>
								<option value="processing">Processing</option>
								<option value="approval_pending">
									Approval
								</option>
								<option value="completed">Completed</option>
								<option value="error">Error</option>
								<option value="cancelled">Cancelled</option>
							</select>
						</div>
					</div>
				</div>

				{/* --- Refresh Button (Top Right) --- */}
				<div className="absolute top-4 right-4 md:top-6 md:right-6 z-30">
					<button
						onClick={() => fetchTasksData()}
						className="p-2.5 rounded-full hover:bg-neutral-700/60 transition-colors text-gray-300"
						data-tooltip-id="refresh-tooltip"
						disabled={loading && tasks.length > 0}
					>
						{loading && tasks.length > 0 ? (
							<IconLoader className="h-6 w-6 animate-spin" />
						) : (
							<IconRefresh className="h-6 w-6" />
						)}
					</button>
					<Tooltip
						id="refresh-tooltip"
						content={
							loading
								? "Refreshing..."
								: "Refresh Tasks (Auto refreshes every minute)"
						}
						place="bottom"
					/>
				</div>

				{/* --- Task List Container --- */}
				<main className="flex-1 w-full max-w-2xl mx-auto py-6 flex flex-col overflow-hidden">
					<div className="flex-grow overflow-y-auto space-y-2 md:pr-2 custom-scrollbar">
						{loading || loadingIntegrations ? (
							<div className="flex justify-center items-center h-full">
								<IconLoader className="w-10 h-10 animate-spin text-white" />
							</div>
						) : filteredTasks.length === 0 ? (
							<p className="text-gray-500 text-center py-16">
								No tasks found matching your criteria.
							</p>
						) : (
							<>
								<CollapsibleSection
									title="Active"
									tasks={activeTasks}
									isOpen={openSections.active}
									toggleOpen={() => toggleSection("active")}
									onViewDetails={setViewingTask}
									onEditTask={handleEditTask}
									onDeleteTask={handleDeleteTask}
								/>
								<CollapsibleSection
									title="Pending Approval"
									tasks={pendingApprovalTasks}
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
									tasks={processingTasks}
									isOpen={openSections.processing}
									toggleOpen={() =>
										toggleSection("processing")
									}
									onViewDetails={setViewingTask}
								/>
								<CollapsibleSection
									title="Completed"
									tasks={completedTasks}
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

				<div className="absolute bottom-0 left-0 right-0 p-4 bg-[#1a1a1a]/80 backdrop-blur-sm border-t border-[#2a2a2a]">
					<div className="max-w-4xl mx-auto">
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
									<div className="space-y-6 pt-4">
										<div>
											<label className="text-sm font-medium text-gray-300 mb-2 block">
												1. What is your goal?
											</label>
											<div className="flex gap-2">
												<input
													type="text"
													placeholder="e.g., Send a daily summary of my calendar to my boss"
													value={generationPrompt}
													onChange={(e) =>
														setGenerationPrompt(
															e.target.value
														)
													}
													className="flex-grow p-3 bg-[#2a2a2a] border border-[#3a3a3a] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#4a9eff]"
												/>
												<button
													onClick={handleGeneratePlan}
													disabled={isGeneratingPlan}
													className="p-3 px-5 bg-[#4a9eff] hover:bg-blue-500 rounded-lg text-white font-semibold transition-colors disabled:opacity-50 flex items-center"
												>
													{isGeneratingPlan ? (
														<IconLoader className="w-5 h-5 animate-spin" />
													) : (
														"Generate Plan"
													)}
												</button>
											</div>
										</div>

										<div>
											<label className="text-sm font-medium text-gray-300 mb-2 block">
												2. Review & Edit Plan
											</label>
											<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
												<input
													type="text"
													placeholder="Describe the overall goal..."
													value={newTaskDescription}
													onChange={(e) =>
														setNewTaskDescription(
															e.target.value
														)
													}
													className="md:col-span-2 p-3 bg-[#2a2a2a] border border-[#3a3a3a] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#4a9eff]"
												/>
												<select
													value={newTaskPriority}
													onChange={(e) =>
														setNewTaskPriority(
															Number(
																e.target.value
															)
														)
													}
													className="p-3 bg-[#2a2a2a] border border-[#3a3a3a] rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#4a9eff] appearance-none"
												>
													<option value={0}>
														High Priority
													</option>
													<option value={1}>
														Medium Priority
													</option>
													<option value={2}>
														Low Priority
													</option>
												</select>
											</div>
										</div>
										<div className="space-y-3">
											<label className="text-sm font-medium text-gray-300">
												Plan Steps
											</label>
											<AnimatePresence>
												{newTaskPlan.map(
													(step, index) => (
														<motion.div
															key={index}
															initial={{
																opacity: 0,
																y: -10
															}}
															animate={{
																opacity: 1,
																y: 0
															}}
															exit={{
																opacity: 0,
																x: -20
															}}
															className="flex items-center gap-3"
														>
															<IconGripVertical className="h-5 w-5 text-gray-500 flex-shrink-0" />
															<select
																value={
																	step.tool ||
																	""
																}
																onChange={(e) =>
																	handleStepChange(
																		index,
																		"tool",
																		e.target
																			?.value
																	)
																}
																className="w-2/5 p-2 bg-[#2a2a2a] border border-[#3a3a3a] rounded-md text-white focus:outline-none focus:ring-2 focus:ring-[#4a9eff] text-sm"
															>
																<option value="">
																	Select a
																	tool...
																</option>
																{availableTools.map(
																	(tool) => {
																		const isConnected =
																			integrations.find(
																				(
																					i
																				) =>
																					i.name ===
																					tool.name
																			)
																				?.connected ||
																			integrations.find(
																				(
																					i
																				) =>
																					i.name ===
																					tool.name
																			)
																				?.auth_type ===
																				"builtin"
																		return (
																			<option
																				key={
																					tool.name
																				}
																				value={
																					tool.name
																				}
																			>
																				{
																					tool.display_name
																				}{" "}
																				{!isConnected &&
																					" (Not Connected)"}
																			</option>
																		)
																	}
																)}
															</select>
															<input
																type="text"
																placeholder="Describe what this step should do..."
																value={
																	step.description
																}
																onChange={(e) =>
																	handleStepChange(
																		index,
																		"description",
																		e.target
																			.value
																	)
																}
																className="flex-grow p-2 bg-[#2a2a2a] border border-[#3a3a3a] rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#4a9eff] text-sm"
															/>
															{!integrations.find(
																(i) =>
																	i.name ===
																	step.tool
															)?.connected &&
																integrations.find(
																	(i) =>
																		i.name ===
																		step.tool
																)?.auth_type !==
																	"builtin" && (
																	<ConnectToolButton
																		toolName={
																			step.tool
																		}
																	/>
																)}
															<button
																onClick={() =>
																	handleRemoveStep(
																		index
																	)
																}
																className="p-2 text-red-400 hover:bg-neutral-700 rounded-full transition-colors"
															>
																<IconX className="h-4 w-4" />
															</button>
														</motion.div>
													)
												)}
											</AnimatePresence>
										</div>

										<div>
											<label className="text-sm font-medium text-gray-300 mb-2 block">
												3. Set Schedule
											</label>
											<ScheduleEditor
												schedule={newSchedule}
												setSchedule={setNewSchedule}
											/>
										</div>

										<div className="flex justify-between items-center">
											<button
												onClick={handleAddStep}
												className="flex items-center gap-1.5 py-2 px-4 rounded-full bg-[#3a3a3a] hover:bg-[#4a4a4a] text-white text-xs font-medium transition-colors"
											>
												<IconPlus className="h-4 w-4" />{" "}
												Add Step
											</button>
											<button
												onClick={handleAddTask}
												disabled={isAdding}
												className="flex items-center gap-2 py-2.5 px-6 rounded-lg bg-[#4a9eff] hover:bg-blue-500 text-white text-sm font-semibold transition-colors disabled:opacity-50"
											>
												{isAdding ? (
													<IconLoader className="h-5 w-5 animate-spin" />
												) : (
													"Save New Plan"
												)}
											</button>
										</div>
									</div>
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

				{/* --- Edit Task Modal --- */}
				{editingTask && (
					<div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4">
						<motion.div
							initial={{ opacity: 0, scale: 0.95 }}
							animate={{ opacity: 1, scale: 1 }}
							exit={{ opacity: 0, scale: 0.95 }}
							className="bg-neutral-800 p-8 rounded-lg shadow-xl w-full max-w-3xl mx-auto max-h-[90vh] flex flex-col"
						>
							<h3 className="text-xl font-semibold mb-6 text-white flex justify-between items-center">
								Edit Task
								<button
									onClick={() => setEditingTask(null)}
									className="text-gray-400 hover:text-white"
								>
									<IconX />
								</button>
							</h3>
							<div className="overflow-y-auto custom-scrollbar pr-4 space-y-6">
								<div>
									<label className="block text-gray-300 text-sm font-medium">
										Description
									</label>
									<input
										type="text"
										value={editingTask.description}
										onChange={(e) =>
											setEditingTask({
												...editingTask,
												description: e.target.value
											})
										}
										className="mt-1 p-3 rounded-md bg-neutral-700 border border-neutral-600 text-white focus:outline-none w-full focus:border-lightblue text-base"
									/>
								</div>
								<div>
									<label className="block text-gray-300 text-sm font-medium">
										Priority
									</label>
									<select
										value={editingTask.priority}
										onChange={(e) =>
											setEditingTask({
												...editingTask,
												priority: Number(e.target.value)
											})
										}
										className="mt-1 p-3 rounded-md bg-neutral-700 border border-neutral-600 text-white focus:outline-none w-full focus:border-lightblue appearance-none text-base"
									>
										<option value={0}>High</option>
										<option value={1}>Medium</option>
										<option value={2}>Low</option>
									</select>
								</div>
								<div>
									<label className="block text-gray-300 text-sm font-medium mb-2">
										Schedule
									</label>
									<ScheduleEditor
										schedule={
											editingTask.schedule || {
												type: "once"
											}
										}
										setSchedule={(newSched) =>
											setEditingTask({
												...editingTask,
												schedule: newSched
											})
										}
									/>
								</div>
								<div className="space-y-3 pt-2">
									<label className="text-sm font-medium text-gray-300">
										Plan Steps
									</label>
									{editingTask.plan?.map((step, index) => (
										<div
											key={index}
											className="flex items-center gap-3"
										>
											<IconGripVertical className="h-5 w-5 text-gray-500 flex-shrink-0" />
											<select
												value={step.tool}
												onChange={(e) =>
													handleEditStepChange(
														index,
														"tool",
														e.target.value
													)
												}
												className="w-1/3 p-2 bg-neutral-700/60 border border-neutral-600 rounded-md text-white focus:outline-none focus:border-lightblue text-sm"
											>
												<option value="">
													Select a tool...
												</option>
												{availableTools.map((tool) => (
													<option
														key={tool.name}
														value={tool.name}
														disabled={
															!integrations.find(
																(i) =>
																	i.name ===
																	tool.name
															)?.connected &&
															integrations.find(
																(i) =>
																	i.name ===
																	tool.name
															)?.auth_type !==
																"builtin"
														}
													>
														{tool.display_name}
														{!integrations.find(
															(i) =>
																i.name ===
																tool.name
														)?.connected &&
															integrations.find(
																(i) =>
																	i.name ===
																	tool.name
															)?.auth_type !==
																"builtin" &&
															" (Not Connected)"}
													</option>
												))}
											</select>
											<input
												type="text"
												placeholder="Describe what this step should do..."
												value={step.description}
												onChange={(e) =>
													handleEditStepChange(
														index,
														"description",
														e.target.value
													)
												}
												className="flex-grow p-2 bg-neutral-700/60 border border-neutral-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:border-lightblue text-sm"
											/>
											{!integrations.find(
												(i) => i.name === step.tool
											)?.connected &&
												integrations.find(
													(i) => i.name === step.tool
												)?.auth_type !== "builtin" && (
													<ConnectToolButton
														toolName={step.tool}
													/>
												)}
											<button
												onClick={() =>
													handleRemoveStepFromEditModal(
														index
													)
												}
												className="p-2 text-red-400 hover:bg-neutral-700 rounded-full transition-colors"
											>
												<IconX className="h-4 w-4" />
											</button>
										</div>
									))}
									<button
										onClick={handleAddStepToEditModal}
										className="flex items-center gap-1.5 py-1.5 px-3 rounded-full bg-neutral-600/70 hover:bg-neutral-600 text-white text-xs font-medium transition-colors"
									>
										<IconPlus className="h-4 w-4" /> Add
										Step
									</button>
								</div>
							</div>
							<div className="flex justify-end gap-4 mt-6 pt-4 border-t border-neutral-700">
								<button
									onClick={() => setEditingTask(null)}
									className="py-2.5 px-5 rounded bg-neutral-600 hover:bg-neutral-500 text-white text-sm font-medium transition-colors"
								>
									Cancel
								</button>
								<button
									onClick={handleUpdateTask}
									className="py-2.5 px-5 rounded bg-green-600 hover:bg-green-500 text-white text-sm font-medium transition-colors"
								>
									Save Changes
								</button>
							</div>
						</motion.div>
					</div>
				)}
			</div>
		</div>
	)
}
const ConnectToolButton = ({ toolName }) => {
	const router = useRouter()
	return (
		<button
			onClick={() => router.push(`/settings?connect=${toolName}`)}
			className="text-xs bg-yellow-600/80 text-white font-semibold py-1 px-3 rounded-md hover:bg-yellow-500 transition-colors whitespace-nowrap"
		>
			Connect
		</button>
	)
}

const CollapsibleSection = ({
	title,
	tasks,
	isOpen,
	toggleOpen,
	integrations,
	...handlers
}) => {
	if (tasks.length === 0 && title !== "Pending Approval") return null // Hide empty sections except for approval
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
						className="overflow-hidden space-y-4"
					>
						{tasks.length > 0 ? (
							tasks.map((task) => (
								<TaskCard
									key={task.task_id}
									task={task}
									integrations={integrations}
									{...handlers}
								/>
							))
						) : (
							<p className="text-gray-500 text-center py-4 italic">
								No tasks in this section.
							</p>
						)}
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

	// Check for missing tools
	let missingTools = []
	if (task.status === "approval_pending" && integrations) {
		const requiredTools = new Set(task.plan?.map((step) => step.tool) || [])
		requiredTools.forEach((toolName) => {
			const integration = integrations.find((i) => i.name === toolName)
			if (integration) {
				const isConnected = integration.connected
				const isBuiltIn = integration.auth_type === "builtin"
				if (!isConnected && !isBuiltIn) {
					missingTools.push(integration.display_name || toolName)
				}
			}
		})
	}

	const getScheduleText = () => {
		if (!task.schedule) return null
		const { frequency, time, days } = task.schedule
		let scheduleText = `Repeats ${frequency}`
		if (time) scheduleText += ` at ${time}`
		if (frequency === "weekly" && days?.length > 0) {
			scheduleText += ` on ${days.join(", ")}`
		}
		return scheduleText
	}
	const scheduleText = getScheduleText()

	const { original_context } = task // Destructure the context

	// Function to render the source information
	const renderTaskSource = () => {
		if (!original_context) return null

		const source = original_context.source || original_context.service_name
		let sourceText = "From an unknown source"
		let icon = <IconHelpCircle size={14} />

		if (source === "journal_block" && original_context.original_content) {
			sourceText = `From Journal: "${original_context.original_content.substring(
				0,
				40
			)}..."`
			icon = <IconBook size={14} />

			// Make journal source clickable
			const pageDate = original_context.page_date
			if (pageDate) {
				return (
					<button
						onClick={(e) => {
							e.stopPropagation() // Prevent card's main onClick
							router.push(`/journal?date=${pageDate}`)
						}}
						className="w-full text-left text-xs text-gray-500 mt-1 flex items-center gap-1.5 italic hover:text-blue-400 transition-colors"
						title={`Go to journal entry on ${pageDate}`}
					>
						{icon}
						<span className="truncate">{sourceText}</span>
					</button>
				)
			}
		} else if (source === "gmail") {
			sourceText = `From Gmail: "${
				original_context.subject || "No Subject"
			}"`
			icon = <IconMail size={14} />
		} else if (source === "gcalendar") {
			sourceText = `From Calendar: "${
				original_context.summary || "No Summary"
			}"`
			icon = <IconCalendarEvent size={14} />
		} else if (source === "chat") {
			sourceText = `From Chat: "${original_context.description}"`
			icon = <IconMessage size={14} />
		}

		// Fallback for non-clickable sources
		return (
			<p
				className="text-xs text-gray-500 mt-1 flex items-center gap-1.5 italic"
				title={sourceText}
			>
				{icon}
				<span className="truncate">{sourceText}</span>
			</p>
		)
	}

	return (
		<div
			key={task.task_id}
			className={cn(
				"flex items-center gap-4 bg-neutral-800 p-4 rounded-lg shadow hover:bg-neutral-700/60 transition-colors duration-150",
				"border-l-4 relative",
				task.enabled === false
					? "border-gray-600"
					: statusInfo.borderColor,
				task.enabled === false ? "opacity-60" : "opacity-100",
				!missingTools.length && "cursor-pointer"
			)}
			onClick={() => !missingTools.length && onViewDetails(task)}
		>
			{/* Status Icon & Priority */}
			<div className="flex flex-col items-center w-20 flex-shrink-0">
				<statusInfo.icon className={cn("h-7 w-7", statusInfo.color)} />
				<span
					className={cn(
						"text-xs mt-1.5 font-semibold",
						priorityInfo.color
					)}
				>
					{priorityInfo.label}
				</span>
			</div>

			{/* Task Details */}
			<div className="flex-grow min-w-0">
				<p
					className="text-base font-normal text-[var(--color-text-primary)]"
					title={task.description}
				>
					{task.description}
				</p>

				{renderTaskSource()}

				{scheduleText && (
					<p className="text-xs text-[var(--color-accent-blue)] mt-1 flex items-center gap-1.5">
						<IconRefresh size={14} />
						<span>{scheduleText}</span>
						{!task.enabled && (
							<span className="font-bold text-yellow-400">
								(Disabled)
							</span>
						)}
					</p>
				)}
				{missingTools.length > 0 ? (
					<div
						className="flex items-center gap-2 mt-2 text-yellow-400 text-xs"
						data-tooltip-id={`missing-tools-tooltip-${task.task_id}`}
					>
						<IconAlertTriangle size={14} />
						<span>Requires: {missingTools.join(", ")}</span>
						<Tooltip
							id={`missing-tools-tooltip-${task.task_id}`}
							content="Please connect these tools in Settings to approve this task."
							place="bottom"
						/>
					</div>
				) : (
					<p className="text-sm text-gray-400 mt-1">
						ID: {task.task_id} | Added:{" "}
						{new Date(task.created_at).toLocaleString()}
					</p>
				)}
				{(task.result || task.error) && (
					<p
						className="text-xs text-gray-500 mt-1 truncate italic"
						title={task.result || task.error}
					>
						Last run result:{" "}
						{typeof task.result === "string"
							? task.result.substring(0, 50) + "..."
							: "[Details in Modal/Log]"}
					</p>
				)}
			</div>

			{/* Actions */}
			<div
				className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
				onClick={(e) => e.stopPropagation()}
			>
				{task.status === "approval_pending" && (
					<>
						<button
							onClick={(e) => {
								e.stopPropagation()
								onApproveTask(task.task_id)
							}}
							className="p-2 rounded-md text-green-400 hover:bg-[var(--color-primary-surface-elevated)] disabled:text-gray-600 disabled:cursor-not-allowed disabled:hover:bg-transparent"
							title={
								missingTools.length
									? `Connect: ${missingTools.join(", ")}`
									: "Approve Plan"
							}
							disabled={missingTools.length > 0}
						>
							<IconCircleCheck className="h-5 w-5" />
						</button>
						<button
							onClick={(e) => {
								e.stopPropagation()
								onEditTask(task)
							}}
							className="p-2 rounded-md text-yellow-400 hover:bg-[var(--color-primary-surface-elevated)]"
							title="Edit Plan"
						>
							<IconPencil className="h-5 w-5" />
						</button>
						<button
							onClick={(e) => {
								e.stopPropagation()
								onDeleteTask(task.task_id)
							}}
							className="p-2 rounded-md text-red-400 hover:bg-[var(--color-primary-surface-elevated)]"
							title="Delete Plan"
						>
							<IconTrash className="h-5 w-5" />
						</button>
					</>
				)}
				{["completed", "error", "cancelled"].includes(task.status) &&
					!task.schedule && (
						<>
							<button
								onClick={(e) => {
									e.stopPropagation()
									onReRunTask(task.task_id)
								}}
								className="p-2 rounded-md text-blue-400 hover:bg-[var(--color-primary-surface-elevated)]"
								title="Re-run Task"
							>
								<IconRefresh className="h-5 w-5" />
							</button>
							<button
								onClick={(e) => {
									e.stopPropagation()
									onDeleteTask(task.task_id)
								}}
								className="p-2 rounded-md text-red-400 hover:bg-[var(--color-primary-surface-elevated)]"
								title="Delete Task"
							>
								<IconTrash className="h-5 w-5" />
							</button>
						</>
					)}
				{task.status === "active" && (
					<>
						<button
							onClick={(e) => {
								e.stopPropagation()
								onEditTask(task)
							}}
							className="p-2 rounded-md text-yellow-400 hover:bg-[var(--color-primary-surface-elevated)]"
							title="Edit Workflow"
						>
							<IconPencil className="h-5 w-5" />
						</button>
						<button
							onClick={(e) => {
								e.stopPropagation()
								onDeleteTask(task.task_id)
							}}
							className="p-2 rounded-md text-red-400 hover:bg-[var(--color-primary-surface-elevated)]"
							title="Delete Workflow"
						>
							<IconTrash className="h-5 w-5" />
						</button>
					</>
				)}
			</div>
		</div>
	)
}

const TaskDetailsModal = ({ task, onClose, onApprove, integrations }) => {
	const statusInfo = statusMap[task.status] || statusMap.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	// Check for missing tools for the modal
	let missingTools = []
	if (task.status === "approval_pending" && integrations) {
		const requiredTools = new Set(task.plan?.map((step) => step.tool) || [])
		requiredTools.forEach((toolName) => {
			const integration = integrations.find((i) => i.name === toolName)
			if (integration) {
				const isConnected = integration.connected
				const isBuiltIn = integration.auth_type === "builtin"
				if (!isConnected && !isBuiltIn) {
					missingTools.push(integration.display_name || toolName)
				}
			}
		})
	}

	const parseResult = (resultText) => {
		if (typeof resultText !== "string" || !resultText) {
			return {
				thoughts: null,
				finalAnswer: null,
				mainContent: resultText
			}
		}

		const thoughtsMatch = resultText.match(/<think>([\s\S]*?)<\/think>/)
		const finalAnswerMatch = resultText.match(
			/<final_answer>([\s\S]*?)<\/final_answer>/
		)

		const thoughts = thoughtsMatch ? thoughtsMatch[1].trim() : null
		const finalAnswer = finalAnswerMatch ? finalAnswerMatch[1].trim() : null

		let mainContent = resultText
			.replace(/<think>[\s\S]*?<\/think>/g, "")
			.replace(/<final_answer>[\s\S]*?<\/final_answer>/g, "")
			.trim()

		// If the only thing left is the final answer (but without tags), don't show it as main content.
		if (mainContent === finalAnswer) {
			mainContent = null
		}

		if (!mainContent && !finalAnswer && resultText && !thoughts) {
			mainContent = resultText
		}

		return { thoughts, finalAnswer, mainContent }
	}

	const { thoughts, finalAnswer, mainContent } = parseResult(task.result)

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<div className="bg-neutral-800 p-8 rounded-lg shadow-xl w-full max-w-3xl mx-auto max-h-[90vh] flex flex-col">
				<div className="flex justify-between items-center mb-6">
					<h3
						className="text-2xl font-semibold text-white truncate"
						title={task.description}
					>
						{task.description}
					</h3>
					<button
						onClick={onClose}
						className="text-gray-400 hover:text-white transition-colors"
					>
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-4 space-y-8">
					{/* Status and Priority */}
					<div className="flex items-center gap-4 text-sm">
						<div className="flex items-center gap-2">
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
						</div>
						<div className="w-px h-4 bg-neutral-600"></div>
						<div className="flex items-center gap-2">
							<span className="text-gray-400">Priority:</span>
							<span
								className={cn(
									"font-semibold",
									priorityInfo.color
								)}
							>
								{priorityInfo.label}
							</span>
						</div>
					</div>

					{/* Plan */}
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

					{/* Progress Updates */}
					{task.progress_updates &&
						task.progress_updates.length > 0 && (
							<div>
								<h4 className="text-lg font-semibold text-gray-300 mb-4">
									Progress
								</h4>
								<div className="space-y-4">
									{task.progress_updates.map(
										(update, index) => (
											<div
												key={index}
												className="flex gap-4"
											>
												{/* Timeline Marker */}
												<div className="flex flex-col items-center">
													<div className="w-4 h-4 bg-blue-500 rounded-full border-2 border-neutral-800"></div>
													{index <
														task.progress_updates
															.length -
															1 && (
														<div className="w-0.5 flex-grow bg-neutral-700"></div>
													)}
												</div>
												{/* Timeline Content */}
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
										)
									)}
								</div>
							</div>
						)}

					{/* Final Result or Error */}
					{(task.result || task.error) && (
						<div className="pt-4 border-t border-neutral-700/50">
							<h4 className="text-lg font-semibold text-gray-200 mb-4">
								Outcome
							</h4>
							{task.result && (
								<div className="space-y-4 text-gray-300">
									{thoughts && (
										<details className="bg-neutral-900/50 rounded-lg p-3 border border-neutral-700">
											<summary className="cursor-pointer text-sm text-gray-400 font-semibold hover:text-white list-none flex items-center gap-2">
												{" "}
												<IconBrain size={16} /> View
												Agent's Thoughts
											</summary>
											<pre className="mt-3 text-xs text-gray-400 whitespace-pre-wrap font-mono bg-transparent p-0">
												{thoughts}
											</pre>
										</details>
									)}
									{mainContent && (
										<div
											className="prose prose-sm prose-invert max-w-none prose-p:my-2 prose-strong:text-white"
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
												className="text-base text-white prose prose-strong:text-white prose-sm max-w-none"
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
							{task.error && (
								<pre className="text-sm bg-red-900/30 p-4 rounded-md text-red-300 whitespace-pre-wrap font-mono border border-red-500/50">
									{task.error}
								</pre>
							)}
						</div>
					)}
				</div>
				<div className="flex justify-end mt-6 pt-4 border-t border-neutral-700 gap-4">
					<button
						onClick={onClose}
						className="py-2.5 px-6 rounded bg-neutral-600 hover:bg-neutral-500 text-white text-sm font-medium transition-colors"
					>
						Close
					</button>
					{task.status === "approval_pending" && (
						<button
							onClick={() => onApprove(task.task_id)}
							className="py-2.5 px-6 rounded bg-green-600 hover:bg-green-500 text-white text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
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
	const handleTypeChange = (type) => setSchedule({ ...schedule, type })
	const handleFrequencyChange = (e) =>
		setSchedule({ ...schedule, frequency: e.target.value })
	const handleTimeChange = (e) =>
		setSchedule({ ...schedule, time: e.target.value })
	const handleDayToggle = (day) => {
		const currentDays = schedule.days || []
		const newDays = currentDays.includes(day)
			? currentDays.filter((d) => d !== day)
			: [...currentDays, day]
		setSchedule({ ...schedule, days: newDays })
	}

	const weekdays = [
		"Monday",
		"Tuesday",
		"Wednesday",
		"Thursday",
		"Friday",
		"Saturday",
		"Sunday"
	]

	return (
		<div className="bg-neutral-700/50 p-4 rounded-lg space-y-4">
			<div className="flex items-center gap-2">
				<button
					onClick={() => handleTypeChange("once")}
					className={cn(
						"px-4 py-1.5 rounded-full text-sm",
						schedule.type === "once"
							? "bg-lightblue text-white"
							: "bg-neutral-600 hover:bg-neutral-500"
					)}
				>
					Run Once
				</button>
				<button
					onClick={() => handleTypeChange("recurring")}
					className={cn(
						"px-4 py-1.5 rounded-full text-sm",
						schedule.type === "recurring"
							? "bg-lightblue text-white"
							: "bg-neutral-600 hover:bg-neutral-500"
					)}
				>
					Recurring
				</button>
			</div>
			{schedule.type === "recurring" && (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label className="text-xs text-gray-400 block mb-1">
							Frequency
						</label>
						<select
							value={schedule.frequency}
							onChange={handleFrequencyChange}
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md text-white focus:outline-none focus:border-lightblue"
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
							value={schedule.time}
							onChange={handleTimeChange}
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md text-white focus:outline-none focus:border-lightblue"
						/>
					</div>
					{schedule.frequency === "weekly" && (
						<div className="md:col-span-2">
							<label className="text-xs text-gray-400 block mb-2">
								Days
							</label>
							<div className="flex flex-wrap gap-2">
								{weekdays.map((day) => (
									<button
										key={day}
										onClick={() => handleDayToggle(day)}
										className={cn(
											"px-3 py-1.5 rounded-full text-xs font-semibold",
											(schedule.days || []).includes(day)
												? "bg-lightblue text-white"
												: "bg-neutral-600 text-gray-300 hover:bg-neutral-500"
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
