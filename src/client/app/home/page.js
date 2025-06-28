"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import "react-tooltip/dist/react-tooltip.css"
import { useRouter } from "next/navigation"
import Sidebar from "@components/Sidebar"
import {
	IconChecklist,
	IconMenu2,
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
	IconMessage
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { motion, useMotionValue, useTransform, useSpring } from "framer-motion"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"
import { useSmoothScroll } from "@hooks/useSmoothScroll"

const ActionCard = ({
	title,
	description,
	icon,
	href,
	accentColor = "blue"
}) => {
	const router = useRouter()
	const ref = useRef(null)

	const x = useMotionValue(0)
	const y = useMotionValue(0)

	const mouseXSpring = useSpring(x)
	const mouseYSpring = useSpring(y)

	const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], ["6deg", "-6deg"])
	const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], ["-6deg", "6deg"])

	const accentColors = {
		blue: "#4a9eff",
		green: "#00c851",
		purple: "#9c27b0",
		orange: "#ff8800"
	}

	const handleMouseMove = (e) => {
		if (!ref.current) return

		const rect = ref.current.getBoundingClientRect()
		const width = rect.width
		const height = rect.height
		const mouseX = e.clientX - rect.left
		const mouseY = e.clientY - rect.top
		const xPct = mouseX / width - 0.5
		const yPct = mouseY / height - 0.5

		x.set(xPct)
		y.set(yPct)
	}

	const handleMouseLeave = () => {
		x.set(0)
		y.set(0)
	}

	return (
		<motion.div
			ref={ref}
			onMouseMove={handleMouseMove}
			onMouseLeave={handleMouseLeave}
			onClick={() => router.push(href)}
			whileHover={{ scale: 1.02 }}
			whileTap={{ scale: 0.98 }}
			style={{
				rotateY,
				rotateX,
				transformStyle: "preserve-3d"
			}}
			className="bg-[var(--color-primary-surface)] rounded-lg border border-[var(--color-primary-surface-elevated)] p-6 lg:p-8 cursor-pointer hover:border-[var(--accent-color)] transition-all duration-300 relative group"
		>
			{/* Subtle glow effect on hover */}
			<div
				className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-20 transition-opacity duration-300 bg-gradient-to-r from-transparent via-[var(--accent-color)] to-transparent"
				style={{ "--accent-color": accentColors[accentColor] }}
			/>

			<div
				style={{
					transform: "translateZ(30px)",
					transformStyle: "preserve-3d"
				}}
				className="flex flex-col items-start text-left relative z-10"
			>
				<div className="mb-4 p-3 rounded-lg bg-[var(--color-primary-surface-elevated)] group-hover:bg-[var(--accent-color)] group-hover:bg-opacity-10 transition-colors duration-300">
					{React.cloneElement(icon, {
						className: `w-6 h-6 text-[var(--accent-color)]`,
						style: { "--accent-color": accentColors[accentColor] }
					})}
				</div>
				<h2 className="text-xl lg:text-2xl font-semibold text-[var(--color-text-primary)] mb-3">
					{title}
				</h2>
				<p className="text-[#b0b0b0] text-sm lg:text-base leading-relaxed">
					{description}
				</p>

				{/* Action indicator */}
				<div
					className="mt-4 flex items-center text-[var(--accent-color)] text-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300"
					style={{ "--accent-color": accentColors[accentColor] }}
				>
					<span>Get started</span>
					<svg
						className="w-4 h-4 ml-2 transform group-hover:translate-x-1 transition-transform duration-300"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2}
							d="M9 5l7 7-7 7"
						/>
					</svg>
				</div>
			</div>
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
				"flex items-center gap-4 bg-neutral-800 p-4 rounded-lg shadow hover:bg-neutral-700/60 transition-colors duration-150",
				"border-l-4 relative group",
				statusInfo.borderColor,
				!missingTools.length && "cursor-pointer"
			)}
			onClick={() => !missingTools.length && onViewDetails(task)}
		>
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
				className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
				onClick={(e) => e.stopPropagation()}
			>
				<button
					onClick={() => onApproveTask(task.task_id)}
					disabled={missingTools.length > 0}
					className="p-2 rounded-md text-green-400 hover:bg-[var(--color-primary-surface-elevated)] disabled:text-gray-600 disabled:cursor-not-allowed disabled:hover:bg-transparent"
					title={
						missingTools.length
							? `Connect: ${missingTools.join(", ")}`
							: "Approve Plan"
					}
				>
					<IconCircleCheck className="h-5 w-5" />
				</button>
				<button
					onClick={onEditTask}
					className="p-2 rounded-md text-yellow-400 hover:bg-[var(--color-primary-surface-elevated)]"
					title="Edit Plan"
				>
					<IconPencil className="h-5 w-5" />
				</button>
				<button
					onClick={() => onDeleteTask(task.task_id)}
					className="p-2 rounded-md text-red-400 hover:bg-[var(--color-primary-surface-elevated)]"
					title="Delete Plan"
				>
					<IconTrash className="h-5 w-5" />
				</button>
			</div>
		</motion.div>
	)
}

const HomePage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [tasks, setTasks] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [loading, setLoading] = useState(true)
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
		try {
			const [tasksResponse, integrationsResponse] = await Promise.all([
				fetch("/api/tasks"),
				fetch("/api/settings/integrations")
			])
			if (!tasksResponse.ok) throw new Error("Failed to fetch tasks")
			if (!integrationsResponse.ok)
				throw new Error("Failed to fetch integrations")

			const tasksData = await tasksResponse.json()
			const integrationsData = await integrationsResponse.json()

			if (Array.isArray(tasksData.tasks)) {
				setTasks(tasksData.tasks)
			}
			if (Array.isArray(integrationsData.integrations)) {
				setIntegrations(integrationsData.integrations)
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
		if (hour < 12) return "Good morning"
		if (hour < 18) return "Good afternoon"
		return "Good evening"
	}

	const pendingApprovalTasks = tasks.filter(
		(t) => t.status === "approval_pending"
	)

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)]">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col overflow-hidden">
				<header className="flex items-center justify-between p-4 border-b border-[var(--color-primary-surface)] md:hidden">
					<button
						onClick={() => setSidebarVisible(true)}
						className="text-[var(--color-text-primary)] hover:text-[var(--color-accent-blue)] transition-colors duration-150"
					>
						<IconMenu2 />
					</button>
				</header>
				<main
					ref={scrollRef}
					className="flex-1 overflow-y-auto p-4 lg:p-8 no-scrollbar flex items-center justify-center"
				>
					<div className="max-w-6xl w-full">
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
							<h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-6">
								Pending Approval
							</h2>
							<div className="space-y-4">
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
											onApproveTask={handleApproveTask}
											onDeleteTask={handleDeleteTask}
										/>
									))
								) : (
									<p className="text-center text-[var(--color-text-secondary)] py-8">
										You have no tasks pending approval.
									</p>
								)}
							</div>
						</motion.div>

						{/* Main Actions */}
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.3 }}
							className="mb-8"
						>
							<h2 className="text-xl font-semibold text-[var(--color-text-primary)] mb-6">
								Quick Actions
							</h2>
							<div
								className="max-w-lg mx-auto"
								style={{ perspective: "1000px" }}
							>
								<ActionCard
									title="Tasks"
									description="Organize your workflow, manage projects, and stay on top of your daily commitments."
									icon={<IconChecklist />}
									href="/tasks"
									accentColor="blue"
								/>
							</div>
						</motion.div>
					</div>
				</main>
			</div>
		</div>
	)
}

export default HomePage
