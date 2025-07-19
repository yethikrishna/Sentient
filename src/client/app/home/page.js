"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import { format, getDay, isSameDay, parseISO } from "date-fns"
import {
	IconSparkles,
	IconCircleCheck,
	IconAlertTriangle,
	IconAlertCircle,
	IconLoader,
	IconMailQuestion,
	IconRefresh,
	IconX,
	IconHelpCircle,
	IconClock,
	IconBook,
	IconBulb,
	IconSettings,
	IconRepeat,
	IconChecklist,
	IconUser,
	IconMessageQuestion,
	IconSend
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { motion, AnimatePresence } from "framer-motion"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"
import EditTaskModal from "@components/tasks/EditTaskModal"
import TaskDetailsModal from "@components/tasks/TaskDetailsModal"

const HelpTooltip = ({ content }) => (
	<div className="fixed bottom-6 left-6 z-40">
		<button
			data-tooltip-id="page-help-tooltip"
			data-tooltip-content={content}
			className="p-1.5 rounded-full text-neutral-500 hover:text-white hover:bg-[var(--color-primary-surface)] pulse-glow-animation"
		>
			<IconHelpCircle size={22} />
		</button>
	</div>
)

const statusMap = {
	pending: { icon: IconClock, color: "text-yellow-400", label: "Pending" },
	processing: {
		icon: IconLoader,
		color: "text-blue-400",
		label: "Processing"
	},
	completed: {
		icon: IconCircleCheck,
		color: "text-green-400",
		label: "Completed"
	},
	error: { icon: IconAlertCircle, color: "text-red-400", label: "Error" },
	default: { icon: IconHelpCircle, color: "text-gray-400", label: "Unknown" }
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

const CommandBar = ({ onSend, isSending }) => {
	const [prompt, setPrompt] = useState("")
	const [assignee, setAssignee] = useState("ai") // 'ai' or 'user'

	const handleSend = () => {
		if (prompt.trim()) {
			onSend(prompt, assignee)
			setPrompt("")
		}
	}

	return (
		<div className="w-full max-w-3xl mx-auto">
			<div className="relative">
				<textarea
					value={prompt}
					onChange={(e) => setPrompt(e.target.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter" && !e.shiftKey) {
							e.preventDefault()
							handleSend()
						}
					}}
					placeholder="Delegate a task, save a note, or ask a question..."
					className="w-full p-4 pr-32 bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-xl resize-none focus:ring-2 focus:ring-[var(--color-accent-blue)] transition-all"
					rows={1}
				/>
				<div className="absolute top-1/2 right-3 -translate-y-1/2 flex items-center gap-2">
					<button
						onClick={() =>
							setAssignee(assignee === "ai" ? "user" : "ai")
						}
						className="p-2 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
						data-tooltip-id="home-tooltip"
						data-tooltip-content={`Assign to: ${assignee === "ai" ? "AI" : "Me"}`}
					>
						{assignee === "ai" ? (
							<IconSparkles className="text-[var(--color-accent-blue)]" />
						) : (
							<IconUser className="text-neutral-400" />
						)}
					</button>
					<button
						onClick={handleSend}
						disabled={isSending || !prompt.trim()}
						className="p-2.5 bg-[var(--color-accent-blue)] rounded-full text-white disabled:opacity-50"
					>
						{isSending ? (
							<IconLoader className="animate-spin" />
						) : (
							<IconSend />
						)}
					</button>
				</div>
			</div>
		</div>
	)
}

const ApprovalCard = ({ task, onApprove, onDisapprove }) => (
	<div className="bg-[var(--color-primary-surface)]/50 p-3 rounded-lg border border-[var(--color-primary-surface-elevated)] space-y-3">
		<p className="text-sm">{task.description}</p>
		<div className="flex items-center justify-end gap-2">
			<button
				onClick={() => onDisapprove(task.task_id)}
				className="text-xs px-3 py-1.5 rounded-md bg-red-500/20 text-red-300 hover:bg-red-500/30"
			>
				Disapprove
			</button>
			<button
				onClick={() => onApprove(task.task_id)}
				className="text-xs px-3 py-1.5 rounded-md bg-green-500/20 text-green-300 hover:bg-green-500/30"
			>
				Approve
			</button>
		</div>
	</div>
)

const ClarificationCard = ({ task, onSubmit }) => {
	const [answer, setAnswer] = useState("")

	const handleSubmit = () => {
		if (!answer.trim()) {
			toast.error("Please provide an answer.")
			return
		}
		const answers = task.clarifying_questions.map((q) => ({
			question_id: q.question_id,
			answer_text: answer
		}))
		onSubmit(task.task_id, answers)
	}

	return (
		<div className="bg-[var(--color-primary-surface)]/50 p-3 rounded-lg border border-[var(--color-primary-surface-elevated)] space-y-3">
			<p className="text-sm italic text-neutral-400">
				{task.clarifying_questions[0].text}
			</p>
			<div className="flex items-center gap-2">
				<input
					type="text"
					value={answer}
					onChange={(e) => setAnswer(e.target.value)}
					className="flex-grow bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-md px-2 py-1 text-sm"
					placeholder="Your answer..."
				/>
				<button
					onClick={handleSubmit}
					className="text-xs px-3 py-1.5 rounded-md bg-[var(--color-accent-blue)] text-white"
				>
					Submit
				</button>
			</div>
		</div>
	)
}

const TodaysTaskItem = ({ task, onView }) => {
	const statusInfo = statusMap[task.status] || statusMap.default
	return (
		<div
			onClick={() => onView(task)}
			className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--color-primary-surface)]/50 cursor-pointer"
		>
			<statusInfo.icon
				className={cn(
					"h-5 w-5 flex-shrink-0",
					statusInfo.color,
					task.status === "processing" && "animate-spin"
				)}
			/>
			<p className="text-sm text-neutral-300 flex-grow truncate">
				{task.description}
			</p>
		</div>
	)
}

const ActionPanel = ({
	tasks,
	onApprove,
	onDisapprove,
	onSubmitClarification,
	onViewTask
}) => {
	const [activeTab, setActiveTab] = useState("today")

	const todaysTasks = useMemo(() => {
		const today = new Date()
		return tasks.filter((task) => {
			if (task.schedule?.type === "once" && task.schedule.run_at) {
				return isSameDay(parseISO(task.schedule.run_at), today)
			}
			if (task.schedule?.type === "recurring") {
				const dayOfWeek = [
					"Sunday",
					"Monday",
					"Tuesday",
					"Wednesday",
					"Thursday",
					"Friday",
					"Saturday"
				][getDay(today)]
				return (
					task.schedule.frequency === "daily" ||
					(task.schedule.frequency === "weekly" &&
						task.schedule.days.includes(dayOfWeek))
				)
			}
			return false
		})
	}, [tasks])

	const pendingApprovalTasks = useMemo(
		() => tasks.filter((t) => t.status === "approval_pending"),
		[tasks]
	)
	const clarificationTasks = useMemo(
		() => tasks.filter((t) => t.status === "clarification_pending"),
		[tasks]
	)

	const tabs = [
		{ id: "today", icon: IconChecklist, count: todaysTasks.length },
		{
			id: "approval",
			icon: IconMailQuestion,
			count: pendingApprovalTasks.length
		},
		{
			id: "clarification",
			icon: IconMessageQuestion,
			count: clarificationTasks.length
		}
	]

	return (
		<div className="w-[400px] h-full bg-[var(--color-primary-surface)]/50 border-l border-[var(--color-primary-surface-elevated)] flex flex-col p-4">
			<div className="flex items-center gap-2 p-1 bg-[var(--color-primary-surface)] rounded-lg mb-4">
				{tabs.map(({ id, icon: Icon, count }) => (
					<button
						key={id}
						onClick={() => setActiveTab(id)}
						className={cn(
							"flex-1 p-2 rounded-md relative",
							activeTab === id && "bg-[var(--color-accent-blue)]"
						)}
					>
						<Icon className="mx-auto" />
						{count > 0 && (
							<span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-xs text-white">
								{count}
							</span>
						)}
					</button>
				))}
			</div>
			<div className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-3">
				{activeTab === "today" &&
					(todaysTasks.length > 0 ? (
						todaysTasks.map((task) => (
							<TodaysTaskItem
								key={task.task_id}
								task={task}
								onView={onViewTask}
							/>
						))
					) : (
						<p className="text-center text-sm text-neutral-500 pt-10">
							No tasks for today.
						</p>
					))}
				{activeTab === "approval" &&
					(pendingApprovalTasks.length > 0 ? (
						pendingApprovalTasks.map((task) => (
							<ApprovalCard
								key={task.task_id}
								task={task}
								onApprove={onApprove}
								onDisapprove={onDisapprove}
							/>
						))
					) : (
						<p className="text-center text-sm text-neutral-500 pt-10">
							Approval queue is clear.
						</p>
					))}
				{activeTab === "clarification" &&
					(clarificationTasks.length > 0 ? (
						clarificationTasks.map((task) => (
							<ClarificationCard
								key={task.task_id}
								task={task}
								onSubmit={onSubmitClarification}
							/>
						))
					) : (
						<p className="text-center text-sm text-neutral-500 pt-10">
							No questions from the AI.
						</p>
					))}
			</div>
		</div>
	)
}

const HomePage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [tasks, setTasks] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [isSending, setIsSending] = useState(false)
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
		} catch (error) {
			toast.error(`Error fetching data: ${error.message}`)
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
		// This function is now just a placeholder to trigger a refresh
		// as the modal handles its own state updates.
		setEditingTask(null)
		fetchData() // Refresh data
	}

	const handleAnswerClarifications = async (taskId, answers) => {
		try {
			const response = await fetch("/api/tasks/answer-clarifications", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId, answers })
			})
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "Failed to submit answers")
			}
			toast.success(
				"Answers submitted! The AI will continue with the task."
			)
			fetchData() // Refresh data
		} catch (error) {
			toast.error(`Error: ${error.message}`)
		}
	}

	const handleSendCommand = async (prompt, assignee) => {
		setIsSending(true)
		try {
			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ prompt, assignee })
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to add task")
			}
			toast.success(data.message || "Task created successfully!")
			fetchData()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSending(false)
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

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] overflow-hidden pl-0 md:pl-20">
			<Tooltip id="home-tooltip" place="top" style={{ zIndex: 9999 }} />
			<Tooltip
				id="page-help-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>

			<div className="flex-1 flex flex-col overflow-y-auto relative custom-scrollbar">
				<HelpTooltip content="This is your Command & Control center. Delegate tasks in the center, and manage ongoing work on the right." />
				<main className="flex-1 overflow-y-auto p-4 lg:p-8 custom-scrollbar">
					<div className="max-w-4xl w-full mx-auto flex flex-col h-full">
						{/* Header Section */}
						<div className="text-center mb-8 lg:mb-12">
							<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)]">
								{getGreeting()},{" "}
								{userDetails?.given_name || "User"}
							</h1>
							<p className="text-lg text-[var(--color-text-secondary)] mt-2">
								What are we doing next?
							</p>
						</div>

						{/* Command Bar */}
						<CommandBar
							onSend={handleSendCommand}
							isSending={isSending}
						/>

						{/* Proactive Assistant Card - Placeholder */}
						<div className="mt-12 bg-gradient-to-br from-[var(--color-primary-surface)] to-transparent p-4 rounded-lg border border-[var(--color-primary-surface-elevated)] flex items-center gap-4">
							<IconBulb className="text-yellow-400" />
							<p className="text-sm text-neutral-300">
								<span className="font-semibold">Pro Tip:</span>{" "}
								Try asking me to 'summarize my unread emails
								from this morning'.
							</p>
							<button className="ml-auto text-neutral-500 hover:text-white">
								<IconX size={18} />
							</button>
						</div>

						{/* Use Cases Section */}
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.4 }}
							className="mt-12 lg:mt-16 flex-grow"
						>
							<h2 className="text-xl font-semibold text-center mb-8 text-[var(--color-text-primary)]">
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
			<ActionPanel
				tasks={tasks}
				onApprove={handleApproveTask}
				onDisapprove={handleDeleteTask}
				onSubmitClarification={handleAnswerClarifications}
				onViewTask={setViewingTask}
			/>
			<AnimatePresence>
				{editingTask && (
					<EditTaskModal
						key={editingTask.task_id}
						task={editingTask}
						onClose={() => setEditingTask(null)}
						onSave={handleUpdateTask}
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
						onDelete={(taskId) => {
							handleDeleteTask(taskId)
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
