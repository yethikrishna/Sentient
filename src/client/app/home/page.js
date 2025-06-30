"use client"

import React, { useState, useEffect, useCallback, useRef, useMemo } from "react"
import "react-tooltip/dist/react-tooltip.css"
import { useRouter } from "next/navigation"
import { format, getDay, isSameDay, parseISO } from "date-fns"
import {
	IconChecklist,
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
	IconMail,
	IconCalendarEvent,
	IconMessage,
	IconChevronUp
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { motion, useMotionValue, useTransform, useSpring } from "framer-motion"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"
import { useSmoothScroll } from "@hooks/useSmoothScroll"

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
					className="text-sm text-blue-400 hover:underline"
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

const TaskCard = ({ task, integrations, onApproveTask, onDeleteTask }) => {
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

	const onEditTask = () => router.push("/tasks")
	const onViewDetails = () => router.push("/tasks")

	return (
		<motion.div
			key={task.task_id}
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, y: -20 }}
			className={cn(
				"flex items-start gap-3 sm:gap-4 bg-gradient-to-br from-[var(--color-primary-surface)] to-neutral-800/60 p-4 rounded-xl shadow-lg transition-all duration-200 border border-transparent hover:border-blue-500/30",
				"relative group",
				!missingTools.length && "cursor-pointer"
			)}
			onClick={(e) => {
				if (e.target.closest("button")) return
				if (missingTools.length > 0) return
				onViewDetails(task)
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
				)}
			</div>

			<div
				className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity z-10"
				onClick={(e) => e.stopPropagation()}
			>
				<button
					onClick={() => onApproveTask(task.task_id)}
					disabled={missingTools.length > 0}
					className="p-2 rounded-md text-green-400 hover:bg-green-500/20 disabled:text-gray-600 disabled:cursor-not-allowed disabled:hover:bg-transparent"
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
					onClick={onEditTask}
					className="p-2 rounded-md text-yellow-400 hover:bg-yellow-500/20"
					data-tooltip-id="home-tooltip"
					data-tooltip-content="Edit Plan"
				>
					<IconPencil className="h-5 w-5" />
				</button>
				<button
					onClick={() => onDeleteTask(task.task_id)}
					className="p-2 rounded-md text-red-400 hover:bg-red-500/20"
					data-tooltip-id="home-tooltip"
					data-tooltip-content="Delete Plan"
				>
					<IconTrash className="h-5 w-5" />
				</button>
			</div>
		</motion.div>
	)
}

const JournalPreviewCard = ({ entry, ...props }) => {
	const router = useRouter()
	return (
		<motion.div
			onClick={() => router.push(`/journal?date=${entry.page_date}`)}
			className="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-primary-surface)]/40 hover:bg-[var(--color-primary-surface)] transition-colors cursor-pointer"
			{...props}
		>
			<IconBook className="h-5 w-5 flex-shrink-0 text-purple-400" />
			<p className="text-sm text-[var(--color-text-secondary)] truncate">
				{entry.content}
			</p>
		</motion.div>
	)
}

const HomePage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [tasks, setTasks] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [todaysJournal, setTodaysJournal] = useState([])
	const [loading, setLoading] = useState(true)
	const [openSections, setOpenSections] = useState({
		pendingApproval: true
	})

	const scrollRef = useRef(null)

	useSmoothScroll(scrollRef)

	const fetchUserDetails = useCallback(async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user details")
			setUserDetails(await response.json())
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
		}
	}, [])

	const fetchData = useCallback(async () => {
		setLoading(true)
		const today = format(new Date(), "yyyy-MM-dd")
		try {
			const [tasksResponse, integrationsResponse, journalResponse] =
				await Promise.all([
					fetch("/api/tasks"),
					fetch("/api/settings/integrations"),
					fetch(`/api/journal?date=${today}`)
				])
			if (!tasksResponse.ok) throw new Error("Failed to fetch tasks")
			if (!integrationsResponse.ok)
				throw new Error("Failed to fetch integrations")
			if (!journalResponse.ok)
				throw new Error("Failed to fetch today's journal entries")

			const tasksData = await tasksResponse.json()
			const integrationsData = await integrationsResponse.json()
			const journalData = await journalResponse.json()

			if (Array.isArray(tasksData.tasks)) {
				setTasks(tasksData.tasks)
			}
			if (Array.isArray(integrationsData.integrations)) {
				setIntegrations(integrationsData.integrations)
			}
			if (Array.isArray(journalData.blocks)) {
				setTodaysJournal(journalData.blocks)
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
				const errorData = await response.json()
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
		if (!window.confirm("Are you sure you want to delete this task?"))
			return
		try {
			const response = await fetch("/api/tasks/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) throw new Error("Failed to delete task")
			toast.success("Task deleted successfully!")
			fetchData()
		} catch (error) {
			toast.error(`Failed to delete task: ${error.message}`)
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

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)]">
			<Tooltip id="home-tooltip" />
			<div className="flex-1 flex flex-col overflow-hidden">
				<main
					ref={scrollRef}
					className="flex-1 overflow-y-auto p-4 lg:p-8 custom-scrollbar flex items-center justify-center"
				>
					<div className="max-w-7xl w-full">
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
								I’m all ears. What’s next?
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
								className="w-full flex justify-between items-center py-3 px-2 text-left hover:bg-neutral-800/30 rounded-lg transition-colors"
							>
								<h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
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
											<TaskCard
												key={task.task_id}
												task={task}
												integrations={integrations}
												onApproveTask={
													handleApproveTask
												}
												onDeleteTask={handleDeleteTask}
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
						<div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
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
								title="Today's Journal"
								items={todaysJournal}
								renderItem={(item, i) => (
									<JournalPreviewCard key={i} entry={item} />
								)}
								viewAllLink="/journal"
								emptyMessage="No journal entries for today."
								icon={<IconBook />}
							/>
						</div>
					</div>
				</main>
			</div>
		</div>
	)
}

export default HomePage
