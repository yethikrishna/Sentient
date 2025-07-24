"use client"

import React, {
	useState,
	useEffect,
	useCallback,
	Suspense,
	useMemo
} from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { parseISO } from "date-fns"
import { IconLoader, IconX } from "@tabler/icons-react"
import { AnimatePresence, motion } from "framer-motion"
import toast from "react-hot-toast"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"
import Script from "next/script"

// New component imports
import TasksHeader from "@components/tasks/TasksHeader"
import AllTasksView from "@components/tasks/AllTasksView"
import TaskDetailsPanel from "@components/tasks/TaskDetailsPanel"

const StorylaneDemoModal = ({ onClose }) => {
	return (
		<>
			<Script async src="https://js.storylane.io/js/v2/storylane.js" />
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
					className="relative bg-gradient-to-br from-white/15 via-white/10 to-white/15 backdrop-blur-2xl p-6 rounded-3xl shadow-2xl w-full max-w-6xl h-[90vh] border border-white/20 flex flex-col overflow-hidden"
				>
					<div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-purple-500/5 to-pink-500/10 rounded-3xl" />
					<div className="absolute inset-0 backdrop-blur-3xl bg-black/20 rounded-3xl border border-white/10 shadow-inner" />
					<div className="absolute -top-4 -right-4 w-24 h-24 bg-gradient-to-br from-blue-400/20 to-purple-400/20 rounded-full blur-2xl animate-pulse" />
					<div className="absolute -bottom-4 -left-4 w-32 h-32 bg-gradient-to-br from-purple-400/20 to-pink-400/20 rounded-full blur-2xl animate-pulse" />

					<div className="relative flex justify-between items-center pb-6 flex-shrink-0 z-10">
						<div>
							<h2 className="text-3xl font-bold bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent drop-shadow-2xl">
								���� Interactive Walkthrough
							</h2>
							<div className="w-1/3 h-1 bg-gradient-to-r from-blue-500/50 via-purple-500/50 to-pink-500/50 rounded-full blur-sm mt-2" />
						</div>
						<button
							onClick={onClose}
							className="relative p-3 rounded-2xl bg-white/10 hover:bg-white/20 backdrop-blur-lg border border-white/20 hover:border-white/30 transition-all duration-300 transform hover:scale-110 shadow-lg group"
						>
							<IconX
								size={20}
								className="text-white/70 group-hover:text-white transition-colors"
							/>
						</button>
					</div>
					<div className="relative flex-1 w-full h-full z-10">
						<iframe
							loading="lazy"
							className="sl-demo"
							src="https://app.storylane.io/demo/d6oo4tbg4fbb?embed=inline"
							name="sl-embed"
							allow="fullscreen"
							allowFullScreen
							style={{
								width: "100%",
								height: "100%",
								border: "1px solid rgba(255,255,255,0.2)",
								boxShadow:
									"0px 0px 30px rgba(59, 130, 246, 0.15)",
								borderRadius: "20px",
								boxSizing: "border-box"
							}}
						></iframe>
					</div>
				</motion.div>
			</motion.div>
		</>
	)
}

function TasksPageContent() {
	const searchParams = useSearchParams()
	const router = useRouter()

	const [tasks, setTasks] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [allTools, setAllTools] = useState([])
	const [isLoading, setIsLoading] = useState(true)

	// Panel State
	const [selectedTask, setSelectedTask] = useState(null)
	const [isDemoModalOpen, setIsDemoModalOpen] = useState(false)

	// View control states
	const [activeTab, setActiveTab] = useState("oneTime")
	const [groupBy, setGroupBy] = useState("status")

	// Keep selectedTask in sync with the main tasks list
	useEffect(() => {
		if (selectedTask) {
			const updatedSelectedTask = tasks.find(
				(t) => t.task_id === selectedTask.task_id
			)
			if (updatedSelectedTask) {
				setSelectedTask(updatedSelectedTask)
			} else {
				// If task is not in the list anymore (e.g., deleted), close the panel.
				setSelectedTask(null)
			}
		}
	}, [tasks, selectedTask])

	// Check for query param to auto-open demo on first visit from onboarding
	useEffect(() => {
		const showDemo = searchParams.get("show_demo")
		if (showDemo === "true") {
			setIsDemoModalOpen(true)
			// Clean the URL so the modal doesn't reappear on refresh
			router.replace("/tasks", { scroll: false })
		}
	}, [searchParams, router])

	useEffect(() => {
		const taskIdParam = searchParams.get("taskId")
		if (taskIdParam && !selectedTask) {
			const taskInList = tasks.find((t) => t.task_id === taskIdParam)
			if (taskInList) {
				setSelectedTask(taskInList)
			} else if (!isLoading) {
				// If not in list, fetch it
				fetch(`/api/tasks/${taskIdParam}`)
					.then((res) => {
						if (!res.ok) throw new Error("Task not found")
						return res.json()
					})
					.then((taskData) => {
						setSelectedTask(taskData)
					})
					.catch(() => toast.error("Could not load the linked task."))
			}
			router.replace("/tasks", { scroll: false })
		}
	}, [searchParams, tasks, isLoading, router, selectedTask])

	const fetchTasks = useCallback(async () => {
		setIsLoading(true)
		try {
			const tasksRes = await fetch("/api/tasks")
			if (!tasksRes.ok) throw new Error("Failed to fetch tasks")
			const tasksData = await tasksRes.json()
			setTasks(Array.isArray(tasksData.tasks) ? tasksData.tasks : [])

			const integrationsRes = await fetch("/api/settings/integrations")
			if (!integrationsRes.ok)
				throw new Error("Failed to fetch integrations")
			const integrationsData = await integrationsRes.json()
			const tools = integrationsData.integrations.map((i) => ({
				name: i.name,
				display_name: i.display_name
			}))
			setAllTools(tools)
			setIntegrations(integrationsData.integrations || [])
		} catch (error) {
			toast.error(`Error fetching data: ${error.message}`)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchTasks()
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [])

	// Listen for custom event from LayoutWrapper to refresh tasks
	useEffect(() => {
		const handleBackendUpdate = () => {
			console.log(
				"Received tasksUpdatedFromBackend event, fetching tasks..."
			)
			toast.success("Task list updated from backend.")
			fetchTasks()
		}
		window.addEventListener("tasksUpdatedFromBackend", handleBackendUpdate)
		return () =>
			window.removeEventListener(
				"tasksUpdatedFromBackend",
				handleBackendUpdate
			)
	}, [fetchTasks])

	// Listen for real-time progress updates from WebSocket
	useEffect(() => {
		const handleProgressUpdate = (event) => {
			const { task_id, run_id, update } = event.detail

			const updateTaskState = (task) => {
				if (!task) return null
				// Ensure runs is an array
				const runs = Array.isArray(task.runs) ? task.runs : []
				const newRuns = runs.map((run) => {
					if (run.run_id === run_id) {
						// Ensure progress_updates is an array
						const progressUpdates = Array.isArray(
							run.progress_updates
						)
							? run.progress_updates
							: []
						return {
							...run,
							progress_updates: [...progressUpdates, update]
						}
					}
					return run
				})
				return { ...task, runs: newRuns }
			}

			setTasks((prevTasks) =>
				prevTasks.map((task) =>
					task.task_id === task_id ? updateTaskState(task) : task
				)
			)

			setSelectedTask((prevSelectedTask) =>
				prevSelectedTask?.task_id === task_id
					? updateTaskState(prevSelectedTask)
					: prevSelectedTask
			)
		}

		window.addEventListener("taskProgressUpdate", handleProgressUpdate)

		return () => {
			window.removeEventListener(
				"taskProgressUpdate",
				handleProgressUpdate
			)
		}
	}, []) // Empty dependency array means this runs once on mount

	const handleAction = useCallback(
		async (actionFn, successMessage, ...args) => {
			const toastId = toast.loading("Processing...")
			try {
				const response = await actionFn(...args)
				if (!response.ok) {
					const errorData = await response.json()
					throw new Error(errorData.error || "Action failed")
				}
				toast.success(successMessage, { id: toastId })
				fetchTasks() // Refresh data on success
			} catch (error) {
				toast.error(`Error: ${error.message}`, { id: toastId })
			}
		},
		[fetchTasks]
	)

	const handleApproveTask = (taskId) =>
		handleAction(
			() =>
				fetch("/api/tasks/approve", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ taskId })
				}),
			"Task approved and scheduled!"
		)

	const handleDeleteTask = (taskId) => {
		if (window.confirm("Are you sure you want to delete this task?")) {
			handleAction(
				() =>
					fetch("/api/tasks/delete", {
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({ taskId })
					}),
				"Task deleted."
			)
		}
	}

	const handleRerunTask = (taskId) =>
		handleAction(
			() =>
				fetch("/api/tasks/rerun", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ taskId })
				}),
			"Task duplicated for re-run."
		)

	const handleAnswerClarifications = (taskId, answers) =>
		handleAction(
			() =>
				fetch("/api/tasks/answer-clarifications", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ taskId, answers })
				}),
			"Answers submitted. Re-planning task."
		)

	const handleToggleEnableTask = (taskId, currentEnabled) => {
		const updatedTask = { taskId, enabled: !currentEnabled }
		handleAction(
			() =>
				fetch("/api/tasks/update", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(updatedTask)
				}),
			`Workflow ${!currentEnabled ? "resumed" : "paused"}.`
		)
	}

	const handleArchiveTask = (taskId) => {
		handleAction(
			() =>
				fetch("/api/tasks/update", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ taskId, status: "archived" })
				}),
			"Task archived."
		)
	}

	const handleSendTaskChatMessage = (taskId, message) =>
		handleAction(
			() =>
				fetch("/api/tasks/chat", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ taskId, message })
				}),
			"Message sent. Re-planning task..."
		)

	const handleUpdateTask = async (updatedTask) => {
		await handleAction(
			() =>
				fetch("/api/tasks/update", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						...updatedTask,
						taskId: updatedTask.task_id
					})
				}),
			"Task updated!"
		)
		// After saving, update the selected task to show the new data
		if (selectedTask && selectedTask.task_id === updatedTask.task_id) {
			const refreshedTasks = await fetch("/api/tasks").then((res) =>
				res.json()
			)
			const newlyUpdatedTask = refreshedTasks.tasks.find(
				(t) => t.task_id === updatedTask.task_id
			)
			setSelectedTask(newlyUpdatedTask || null)
		}
	}

	const workflowTasks = useMemo(
		() => tasks.filter((t) => t.schedule?.type === "recurring"),
		[tasks]
	)
	const oneOffTasks = useMemo(
		() =>
			tasks.filter(
				(t) => t.schedule?.type === "once" || !t.schedule?.type
			),
		[tasks]
	)

	return (
		<div className="flex-1 flex h-screen bg-dark-surface text-white overflow-hidden font-Inter">
			<Tooltip
				id="tasks-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>

			<div className="flex flex-1 overflow-hidden relative bg-dark-surface md:pl-20 pb-16 md:pb-0">
				<main
					className={cn(
						"flex-1 flex flex-col overflow-hidden",
						selectedTask && "hidden md:flex"
					)}
				>
					<TasksHeader
						onOpenDemo={() => setIsDemoModalOpen(true)}
						activeTab={activeTab}
						onTabChange={setActiveTab}
						groupBy={groupBy}
						onGroupChange={setGroupBy}
					/>
					{isLoading ? (
						<div className="flex justify-center items-center flex-1">
							<IconLoader className="w-8 h-8 animate-spin text-[var(--color-accent-blue)]" />
						</div>
					) : (
						<div className="flex-1 overflow-hidden">
							<AllTasksView
								tasks={[...oneOffTasks, ...workflowTasks]}
								onViewDetails={setSelectedTask}
								activeTab={activeTab}
								groupBy={groupBy}
								onTabChange={setActiveTab}
								onGroupChange={setGroupBy}
								onTaskAdded={fetchTasks}
							/>
						</div>
					)}
				</main>

				<TaskDetailsPanel
					className={cn(selectedTask ? "flex" : "hidden md:flex")}
					task={selectedTask}
					allTools={allTools}
					integrations={integrations}
					onClose={() => setSelectedTask(null)}
					onSave={handleUpdateTask}
					onApprove={(taskId) => {
						handleApproveTask(taskId)
						setSelectedTask(null)
					}}
					onDelete={(taskId) => {
						handleDeleteTask(taskId)
						setSelectedTask(null)
					}}
					onRerun={(taskId) => {
						handleRerunTask(taskId)
						setSelectedTask(null)
					}}
					onAnswerClarifications={handleAnswerClarifications}
					onArchiveTask={(taskId) => {
						handleArchiveTask(taskId)
						setSelectedTask(null)
					}}
					onSendChatMessage={handleSendTaskChatMessage}
				/>
			</div>

			<AnimatePresence>
				{isDemoModalOpen && (
					<StorylaneDemoModal
						onClose={() => setIsDemoModalOpen(false)}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}

export default function TasksPage() {
	return (
		<Suspense
			fallback={
				<div className="flex-1 flex h-screen bg-dark-surface text-white overflow-hidden justify-center items-center">
					<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
				</div>
			}
		>
			<TasksPageContent />
		</Suspense>
	)
}
