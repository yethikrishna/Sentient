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
import { IconLoader } from "@tabler/icons-react"
import { AnimatePresence } from "framer-motion"
import toast from "react-hot-toast"
import { Tooltip } from "react-tooltip"

// New component imports
import TasksHeader from "@components/tasks/TasksHeader"
import AllTasksView from "@components/tasks/AllTasksView"

// Existing component imports (modals remain)
import TaskDetailsModal from "@components/tasks/TaskDetailsModal"
import EditTaskModal from "@components/tasks/EditTaskModal"

function TasksPageContent() {
	const searchParams = useSearchParams()
	const router = useRouter()

	const [tasks, setTasks] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [allTools, setAllTools] = useState([])
	const [isLoading, setIsLoading] = useState(true)

	// Modal States
	const [selectedTask, setSelectedTask] = useState(null) // For viewing details
	const [editingTask, setEditingTask] = useState(null) // For editing

	useEffect(() => {
		const taskIdParam = searchParams.get("taskId")
		if (taskIdParam && !selectedTask && !editingTask) {
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
	}, [searchParams, tasks, isLoading, router, selectedTask, editingTask])

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

	const handleMarkComplete = (taskId) => {
		handleAction(
			() =>
				fetch("/api/tasks/update", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ taskId, status: "completed" })
				}),
			"Task marked as complete."
		)
	}

	const handleAssigneeChange = (taskId, newAssignee) => {
		const successMessage =
			newAssignee === "ai"
				? "Task assigned to AI for planning."
				: "Task assigned to you."
		handleAction(
			() =>
				fetch("/api/tasks/update", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ taskId, assignee: newAssignee })
				}),
			successMessage
		)
	}

	const handleUpdateTask = async (updatedTask) => {
		handleAction(
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
		<div className="flex h-screen bg-gradient-to-br from-neutral-900 via-black to-neutral-900 text-white overflow-hidden pl-0 md:pl-20">
			<Tooltip
				id="tasks-tooltip"
				place="right-start"
				style={{ zIndex: 9999 }}
			/>

			<main className="flex-1 flex flex-col overflow-hidden relative">
				<TasksHeader />
				{isLoading ? (
					<div className="flex justify-center items-center flex-1">
						<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
					</div>
				) : (
					<div className="p-4 md:p-6 flex-1 overflow-y-auto custom-scrollbar">
						<AllTasksView
							tasks={[...oneOffTasks, ...workflowTasks]}
							onViewDetails={setSelectedTask}
							onEditTask={setEditingTask}
							onDeleteTask={handleDeleteTask}
							onRerunTask={handleRerunTask}
							onMarkComplete={handleMarkComplete}
							onAssigneeChange={handleAssigneeChange}
							onTaskAdded={fetchTasks}
						/>
					</div>
				)}
			</main>

			<AnimatePresence>
				{selectedTask && (
					<TaskDetailsModal
						task={selectedTask}
						onClose={() => setSelectedTask(null)}
						onEdit={(taskToEdit) => {
							setEditingTask(taskToEdit)
							setSelectedTask(null)
						}}
						onApprove={handleApproveTask}
						onDelete={(taskId) => handleDeleteTask(taskId)}
						integrations={integrations}
						onAnswerClarifications={handleAnswerClarifications}
						onArchiveTask={handleArchiveTask}
						onMarkComplete={handleMarkComplete}
						onUpdateTask={handleUpdateTask}
					/>
				)}
				{editingTask && (
					<EditTaskModal
						task={editingTask}
						onClose={() => setEditingTask(null)}
						onSave={(updatedTask) => {
							handleUpdateTask(updatedTask)
							setEditingTask(null)
						}}
						integrations={integrations}
						allTools={allTools}
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
				<div className="flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] overflow-hidden pl-0 md:pl-20 justify-center items-center">
					<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
				</div>
			}
		>
			<TasksPageContent />
		</Suspense>
	)
}
