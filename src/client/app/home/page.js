"use client"

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react"
import { useRouter } from "next/navigation"
import { format, getDay, isSameDay, parseISO } from "date-fns"
import {
	IconSparkles,
	IconCircleCheck,
	IconPencil,
	IconTrash,
	IconAlertTriangle,
	IconAlertCircle,
	IconLoader,
	IconMailQuestion,
	IconRefresh,
	IconX,
	IconHelpCircle,
	IconPlayerPlay,
	IconClock,
	IconBook,
	IconChevronUp,
	IconBulb,
	IconSettings,
	IconRepeat,
	IconChecklist,
	IconRepeat as HelpIcon
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import {
	motion,
	AnimatePresence,
	useMotionValue,
	useTransform,
	useSpring
} from "framer-motion"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"
import { usePostHog } from "posthog-js/react" // eslint-disable-line
import EditTaskModal from "@components/tasks/EditTaskModal"
import TaskDetailsModal from "@components/tasks/TaskDetailsModal"

const HelpTooltip = ({ content }) => (
	<div className="absolute top-6 right-6 z-40">
		<button
			data-tooltip-id="page-help-tooltip"
			data-tooltip-content={content}
			className="p-1.5 rounded-full text-neutral-500 hover:text-white hover:bg-[var(--color-primary-surface)] pulse-glow-animation"
		>
			<IconHelpCircle size={22} />
		</button>
	</div>
)

const PreviewColumn = ({
	title,
	items,
	renderItem,
	viewAllLink,
	emptyMessage,
	icon
}) => {
	const router = useRouter()
	return (
		<motion.div className="bg-gradient-to-br from-[var(--color-primary-surface)]/50 to-transparent p-6 rounded-2xl border border-[var(--color-primary-surface-elevated)] h-full flex flex-col">
			<div className="flex justify-between items-center mb-6">
				<h2 className="text-xl font-semibold text-[var(--color-text-primary)] flex items-center gap-3">
					{icon}
					{title}
				</h2>
				<button
					onClick={() => router.push(viewAllLink)}
					className="text-sm text-[var(--color-accent-blue)] hover:underline"
				>
					View all
				</button>
			</div>
			<div className="space-y-3 overflow-y-auto custom-scrollbar flex-1 pr-2">
				{items.length > 0 ? (
					items.map((item, index) => renderItem(item, index))
				) : (
					<p className="text-center text-[var(--color-text-secondary)] py-10">
						{emptyMessage}
					</p>
				)}
			</div>
		</motion.div>
	)
}

const NotePreviewCard = ({ note, ...props }) => {
	const router = useRouter()
	return (
		<motion.div
			onClick={() => router.push("/notes")}
			className="flex items-start gap-3 p-3 rounded-lg bg-[var(--color-primary-surface)]/40 hover:bg-[var(--color-primary-surface)] transition-colors cursor-pointer"
			{...props}
		>
			<p className="text-sm text-[var(--color-text-secondary)] truncate">
				{note.content}
			</p>
		</motion.div>
	)
}

const TaskPreviewCard = ({ task, ...props }) => {
	const router = useRouter()
	const statusInfo = statusMap[task.status] || statusMap.default
	return (
		<motion.div
			onClick={() => router.push("/tasks")}
			className="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-primary-surface)]/40 hover:bg-[var(--color-primary-surface)] transition-colors cursor-pointer"
			{...props}
		>
			<statusInfo.icon
				className={cn("h-5 w-5 flex-shrink-0", statusInfo.color)}
			/>
			<p className="text-sm text-[var(--color-text-secondary)] truncate">
				{task.description}
			</p>
		</motion.div>
	)
}

const statusMap = {
	pending: {
		icon: IconClock,
		color: "text-[var(--color-status-pending)]",
		borderColor: "border-[var(--color-status-pending)]",
		label: "Pending"
	},
	processing: {
		icon: IconPlayerPlay,
		color: "text-[var(--color-accent-blue)]",
		borderColor: "border-[var(--color-accent-blue)]",
		label: "Processing"
	},
	completed: {
		icon: IconCircleCheck,
		color: "text-[var(--color-accent-green)]",
		borderColor: "border-[var(--color-accent-green)]",
		label: "Completed"
	},
	error: {
		icon: IconAlertCircle,
		color: "text-[var(--color-accent-red)]",
		borderColor: "border-[var(--color-accent-red)]",
		label: "Error"
	},
	approval_pending: {
		icon: IconMailQuestion,
		color: "text-[var(--color-accent-purple)]",
		borderColor: "border-[var(--color-accent-purple)]",
		label: "Approval Pending"
	},
	active: {
		// New status for recurring tasks
		icon: IconRefresh,
		color: "text-[var(--color-accent-green)]",
		label: "Active"
	},
	cancelled: {
		icon: IconX,
		color: "text-[var(--color-text-muted)]",
		borderColor: "border-[var(--color-text-muted)]",
		label: "Cancelled"
	},
	default: {
		icon: IconHelpCircle,
		color: "text-[var(--color-text-secondary)]",
		borderColor: "border-[var(--color-text-secondary)]",
		label: "Unknown"
	}
}

const priorityMap = {
	0: { label: "High", color: "text-[var(--color-accent-red)]" },
	1: { label: "Medium", color: "text-[var(--color-accent-orange)]" },
	2: { label: "Low", color: "text-[var(--color-accent-green)]" },
	default: { label: "Unknown", color: "text-[var(--color-text-muted)]" }
}

const TaskKanbanCard = ({
	task,
	integrations,
	onApproveTask,
	onDeleteTask,
	onEditTask: onEditTaskProp,
	onViewDetails: onViewDetailsProp
}) => {
	const router = useRouter()
	const statusInfo = statusMap[task.status] || statusMap.default

	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	const onEditTask = () => onEditTaskProp(task)
	const onViewDetails = () => onViewDetailsProp(task)
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

	return (
		<motion.div
			key={task.task_id}
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, y: -20 }}
			className={cn(
				"flex items-start gap-3 sm:gap-4 bg-gradient-to-br from-[var(--color-primary-surface)] to-neutral-800/60 p-4 rounded-xl shadow-lg transition-all duration-200 border border-transparent hover:border-[var(--color-accent-blue)]/30",
				"relative group",
				!missingTools.length && "cursor-pointer"
			)}
			onClick={(e) => {
				if (e.target.closest("button")) return
				if (missingTools.length > 0) return
				onViewDetails()
			}}
		>
			<div className="flex flex-col items-center w-16 text-center md:w-20 flex-shrink-0">
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

			<div className="flex-grow min-w-0">
				<p
					className="text-base font-normal text-[var(--color-text-primary)]"
					title={task.description}
				>
					{task.description}
				</p>

				{missingTools.length > 0 && (
					<div
						className="flex items-center gap-2 mt-2 text-[var(--color-accent-orange)] text-xs"
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
				)}
			</div>

			<div
				className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity z-10"
				onClick={(e) => e.stopPropagation()}
			>
				<button
					onClick={() => onApproveTask(task.task_id)}
					disabled={missingTools.length > 0}
					className="p-2 rounded-md text-[var(--color-accent-green)] hover:bg-[var(--color-accent-green)]/20 disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed disabled:hover:bg-transparent"
					data-tooltip-id="home-tooltip"
					data-tooltip-content={
						missingTools.length
							? `Connect: ${missingTools.join(", ")}`
							: "Approve Plan"
					}
				>
					<IconCircleCheck className="h-5 w-5" />
				</button>
				<button
					onClick={() => onEditTask(task)}
					className="p-2 rounded-md text-[var(--color-accent-orange)] hover:bg-[var(--color-accent-orange)]/20"
					data-tooltip-id="home-tooltip"
					data-tooltip-content="Edit Plan"
				>
					<IconPencil className="h-5 w-5" />
				</button>
				<button
					onClick={() => onDeleteTask(task.task_id)}
					className="p-2 rounded-md text-[var(--color-accent-red)] hover:bg-[var(--color-accent-red)]/20"
					data-tooltip-id="home-tooltip"
					data-tooltip-content="Delete Plan"
				>
					<IconTrash className="h-5 w-5" />
				</button>
			</div>
		</motion.div>
	)
}

const IdeaCard = ({ icon, title, description, onClick, cta }) => (
	<motion.div
		whileHover={{ y: -5, boxShadow: "0 10px 20px rgba(0,0,0,0.2)" }}
		className="bg-gradient-to-br from-[var(--color-primary-surface)] to-neutral-800/60 p-6 rounded-2xl border border-[var(--color-primary-surface-elevated)] flex flex-col cursor-pointer"
		onClick={onClick}
	>
		<div className="flex items-center gap-4 mb-4">
			<div className="p-2 bg-[var(--color-accent-blue)]/20 rounded-lg text-[var(--color-accent-blue)]">
				{icon}
			</div>
			<h4 className="text-lg font-semibold text-white">{title}</h4>
		</div>
		<p className="text-sm text-[var(--color-text-secondary)] flex-grow mb-6">
			{description}
		</p>
		<div className="text-right">
			<span className="text-sm font-semibold text-[var(--color-accent-blue)] hover:underline">
				{cta} &rarr;
			</span>
		</div>
	</motion.div>
)

const HomePage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [tasks, setTasks] = useState([])
	const [notes, setNotes] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [loading, setLoading] = useState(true) // For main data
	const [openSections, setOpenSections] = useState({
		pendingApproval: true
	})
	const router = useRouter()
	const [editingTask, setEditingTask] = useState(null)
	const [viewingTask, setViewingTask] = useState(null)
	const [allTools, setAllTools] = useState([])

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/data")
			if (!response.ok) throw new Error("Failed to fetch user details")
			const result = await response.json()
			const userName =
				result?.data?.personalInfo?.name ||
				result?.data?.onboardingAnswers?.["user-name"]
			setUserDetails({ given_name: userName || "User" })
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
			setUserDetails({ given_name: "User" })
		}
	}, [])

	const fetchData = useCallback(async () => {
		setLoading(true)
		try {
			const todayStr = format(new Date(), "yyyy-MM-dd")
			const [tasksResponse, integrationsResponse, notesResponse] =
				await Promise.all([
					fetch("/api/tasks"),
					fetch("/api/settings/integrations"),
					fetch(`/api/notes?date=${todayStr}`)
				])
			if (!tasksResponse.ok) throw new Error("Failed to fetch tasks")
			if (!notesResponse.ok) throw new Error("Failed to fetch notes")
			if (!integrationsResponse.ok)
				throw new Error("Failed to fetch integrations")

			const tasksData = await tasksResponse.json()
			const integrationsData = await integrationsResponse.json()

			if (Array.isArray(integrationsData.integrations)) {
				setIntegrations(integrationsData.integrations)
				const tools = integrationsData.integrations.map((i) => ({
					name: i.name,
					display_name: i.display_name
				}))
				setAllTools(tools)
			}
			if (Array.isArray(tasksData.tasks)) {
				setTasks(tasksData.tasks)
			}
			const notesData = await notesResponse.json()
			if (Array.isArray(notesData.notes)) {
				setNotes(notesData.notes)
			}
		} catch (error) {
			toast.error(`Error fetching data: ${error.message}`)
		} finally {
			setLoading(false)
		}
	}, [])

	const handleApproveTask = async (taskId) => {
		if (!taskId) return
		try {
			const response = await fetch("/api/tasks/approve", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}))
				throw new Error(errorData.error || "Approval failed")
			}
			toast.success("Plan approved! Task has been queued for execution.")
			fetchData() // Refresh data
		} catch (error) {
			toast.error(`Error approving task: ${error.message}`)
			fetchData() // Re-fetch to revert optimistic update on error
		}
	}

	const handleDeleteTask = async (taskId) => {
		if (!taskId) return
		const taskToDelete = tasks.find((t) => t.task_id === taskId)
		if (!window.confirm("Are you sure you want to delete this task?"))
			return
		try {
			const response = await fetch("/api/tasks/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId: taskId })
			})
			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}))
				throw new Error(errorData.error || "Failed to delete task")
			}
			fetchData()
		} catch (error) {
			toast.error(`Failed to delete task: ${error.message}`)
		}
	}

	const handleUpdateTask = async () => {
		if (!editingTask) return
		try {
			const response = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					...editingTask,
					taskId: editingTask.task_id
				})
			})
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error)
			}
			toast.success("Task updated successfully!")
			setEditingTask(null)
			fetchData() // Refresh data
		} catch (error) {
			toast.error(`Failed to update task: ${error.message}`)
		}
	}

	useEffect(() => {
		fetchUserDetails()
		fetchData()
	}, [fetchUserDetails, fetchData])

	const getGreeting = () => {
		const hour = new Date().getHours()
		if (hour < 12) return "Good Morning"
		if (hour < 18) return "Good Afternoon"
		return "Good Evening"
	}

	const pendingApprovalTasks = useMemo(
		() => tasks.filter((t) => t.status === "approval_pending"),
		[tasks]
	)

	const todaysTasks = useMemo(() => {
		const today = new Date()
		const todaysEvents = []

		tasks.forEach((task) => {
			if (task.enabled === false) return

			if (task.schedule?.type === "recurring") {
				const dayOfWeek = getDay(today) // Sunday is 0
				const dayName = [
					"Sunday",
					"Monday",
					"Tuesday",
					"Wednesday",
					"Thursday",
					"Friday",
					"Saturday"
				][dayOfWeek]

				let shouldRun = false
				if (task.schedule.frequency === "daily") {
					shouldRun = true
				} else if (
					task.schedule.frequency === "weekly" &&
					task.schedule.days.includes(dayName)
				) {
					shouldRun = true
				}

				if (shouldRun) {
					todaysEvents.push(task)
				}
			}

			if (task.schedule?.type === "once" && task.schedule.run_at) {
				if (isSameDay(parseISO(task.schedule.run_at), today)) {
					todaysEvents.push(task)
				}
			}
		})
		return todaysEvents
	}, [tasks])

	const todaysNotes = useMemo(() => {
		const today = new Date()
		return notes.filter(
			(note) =>
				note.note_date && isSameDay(parseISO(note.note_date), today)
		)
	}, [notes])

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] overflow-x-hidden pl-0 md:pl-20">
			<Tooltip id="home-tooltip" style={{ zIndex: 9999 }} />
			<Tooltip id="page-help-tooltip" style={{ zIndex: 9999 }} />
			<div className="flex-1 flex flex-col overflow-hidden relative">
				<HelpTooltip content="This is your Home page. See tasks pending your approval and get a glimpse of your day's tasks and notes." />
				<main className="flex-1 overflow-y-auto p-4 lg:p-8 custom-scrollbar">
					<div className="max-w-7xl w-full mx-auto">
						{/* Header Section */}
						<div className="mb-8 lg:mb-12">
							<motion.div
								initial={{ opacity: 0, y: 20 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.5 }}
								className="flex items-center mb-3"
							>
								<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)]">
									{getGreeting()},{" "}
									{userDetails?.given_name || "User"}
								</h1>
								<IconSparkles className="w-6 h-6 text-[var(--color-accent-blue)] ml-3 animate-pulse" />
							</motion.div>
							<motion.p
								initial={{ opacity: 0, y: 20 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.5, delay: 0.1 }}
								className="text-lg text-[var(--color-text-secondary)]"
							>
								I'm all ears. What’s next?
							</motion.p>
						</div>

						{/* Pending Approval Section */}
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.2 }}
							className="mb-8 lg:mb-12"
						>
							<button
								onClick={() =>
									setOpenSections((p) => ({
										...p,
										pendingApproval: !p.pendingApproval
									}))
								}
								className="w-full flex justify-between items-center py-3 px-2 text-left hover:bg-[var(--color-primary-surface)]/50 rounded-lg transition-colors"
							>
								<h2 className="text-xl font-semibold text-[var(--color-text-primary)] flex items-center gap-3">
									<IconMailQuestion className="text-[var(--color-accent-purple)]" />
									Pending Approval (
									{pendingApprovalTasks.length})
								</h2>
								<IconChevronUp
									className={cn(
										"transform transition-transform duration-200",
										!openSections.pendingApproval &&
											"rotate-180"
									)}
								/>
							</button>
							{openSections.pendingApproval && (
								<div className="space-y-4 mt-4">
									{loading ? (
										<div className="flex justify-center items-center p-8">
											<IconLoader className="w-8 h-8 animate-spin text-[var(--color-accent-blue)]" />
										</div>
									) : pendingApprovalTasks.length > 0 ? (
										pendingApprovalTasks.map((task) => (
											<TaskKanbanCard
												key={task.task_id}
												task={task}
												integrations={integrations}
												onApproveTask={
													handleApproveTask
												}
												onDeleteTask={handleDeleteTask}
												onEditTask={setEditingTask}
												onViewDetails={setViewingTask}
											/>
										))
									) : (
										<p className="text-center text-[var(--color-text-secondary)] py-8">
											You have no tasks pending approval.
										</p>
									)}
								</div>
							)}
						</motion.div>

						{/* Today's Previews */}
						<div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto w-full">
							<PreviewColumn
								title="Today's Agenda"
								items={todaysTasks}
								renderItem={(item, i) => (
									<TaskPreviewCard key={i} task={item} />
								)}
								viewAllLink="/tasks"
								emptyMessage="No tasks scheduled for today."
								icon={<IconChecklist />}
							/>
							<PreviewColumn
								title="Today's Notes"
								items={todaysNotes}
								renderItem={(item, i) => (
									<NotePreviewCard key={i} note={item} />
								)}
								viewAllLink="/notes"
								emptyMessage="No notes for today."
								icon={<IconBook />}
							/>
						</div>

						{/* Use Cases Section */}
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.4 }}
							className="mt-12 lg:mt-16"
						>
							<h2 className="text-2xl font-semibold text-center mb-8 text-[var(--color-text-primary)]">
								What's Possible with Sentient?
							</h2>
							<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
								<IdeaCard
									icon={<IconRepeat size={24} />}
									title="Automate Reports"
									description="Set up a recurring task to search your Gmail for weekly reports and summarize them in a Google Doc."
									cta="Create a recurring task"
									onClick={() => router.push("/tasks")}
								/>
								<IdeaCard
									icon={<IconSettings size={24} />}
									title="Personalize Your AI"
									description="Teach Sentient about your communication style and preferences in the Settings page."
									cta="Customize personality"
									onClick={() => router.push("/settings")}
								/>
								<IdeaCard
									icon={<IconBulb size={24} />}
									title="Never Forget an Idea"
									description="Use the Tasks page to jot down thoughts, and let Sentient proactively create tasks and reminders for you."
									cta="Go to Tasks"
									onClick={() => router.push("/tasks")}
								/>
							</div>
						</motion.div>
					</div>
				</main>
			</div>
			<AnimatePresence>
				{editingTask && (
					<EditTaskModal
						key={editingTask.task_id}
						task={editingTask}
						onClose={() => setEditingTask(null)}
						onSave={handleUpdateTask}
						setTask={setEditingTask}
						allTools={allTools}
						integrations={integrations}
					/>
				)}
				{viewingTask && (
					<TaskDetailsModal
						task={viewingTask}
						onClose={() => setViewingTask(null)}
						onApprove={(taskId) => {
							handleApproveTask(taskId)
							setViewingTask(null)
						}}
						integrations={integrations}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}

export default HomePage
