"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import {
	format,
	addDays,
	subDays,
	startOfToday,
	parseISO,
	isSameDay,
	eachDayOfInterval,
	getDay
} from "date-fns"
import {
	IconLoader,
	IconHelpCircle,
	IconPlus,
	IconCircleCheck,
	IconPencil,
	IconTrash,
	IconRefresh
} from "@tabler/icons-react"
import { AnimatePresence } from "framer-motion"
import toast from "react-hot-toast"
import { Tooltip } from "react-tooltip"
import { cn } from "@utils/cn"

// New component imports
import TasksHeader from "@components/tasks/TasksHeader"
import WeeklyKanban from "@components/tasks/WeeklyKanban"
import TasksSidebar from "@components/tasks/TasksSidebar"
// Existing component imports (modals remain)
import AddTaskModal from "@components/tasks/AddTaskModal"
import TaskDetailsModal from "@components/tasks/TaskDetailsModal"
import EditTaskModal from "@components/tasks/EditTaskModal"

export default function TasksPage() {
	const router = useRouter()
	const searchParams = useSearchParams()

	const [viewingTask, setViewingTask] = useState(null)
	const [editingTask, setEditingTask] = useState(null)
	const [activeTab, setActiveTab] = useState("calendar")
	const [viewDate, setViewDate] = useState(() => {
		const dateParam = searchParams.get("date")
		return dateParam ? parseISO(dateParam) : startOfToday()
	})

	// New states for calendar/tasks features
	const [isSidebarOpen, setIsSidebarOpen] = useState(true)

	const [allTasks, setAllTasks] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [integrations, setIntegrations] = useState([])

	// Modal states
	const [isAddingTask, setIsAddingTask] = useState(false)

	const fetchData = useCallback(async () => {
		setIsLoading(true)
		try {
			const [tasksResponse, integrationsResponse] = await Promise.all([
				fetch("/api/tasks"),
				fetch("/api/settings/integrations")
			])

			if (!tasksResponse.ok) throw new Error("Failed to fetch tasks")
			const tasksData = await tasksResponse.json()
			const fetchedTasks = Array.isArray(tasksData.tasks)
				? tasksData.tasks
				: []
			setAllTasks(fetchedTasks)

			if (integrationsResponse.ok) {
				const integrationsData = await integrationsResponse.json()
				setIntegrations(integrationsData.integrations || [])
			} else {
				throw new Error("Failed to fetch integrations")
			}
		} catch (error) {
			toast.error(`Error fetching data: ${error.message}`)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchData() // eslint-disable-line
	}, [fetchData])

	// Date navigation functions for CalendarHeader
	const onDayChange = useCallback(
		(amount) => {
			const newDate = addDays(viewDate, amount)
			router.push(`/tasks?date=${format(newDate, "yyyy-MM-dd")}`, {
				scroll: false
			})
			setViewDate(newDate)
		},
		[router, viewDate]
	)

	const onWeekChange = useCallback(
		(amount) => {
			// A "week" shift in this context means shifting by 3 days for the 3-day Kanban view
			const newDate = addDays(viewDate, amount * 3)
			router.push(`/tasks?date=${format(newDate, "yyyy-MM-dd")}`, {
				scroll: false
			})
			setViewDate(newDate)
		},
		[router, viewDate]
	)

	const handleTaskDrop = async (taskItem, newDate) => {
		if (taskItem.schedule?.type !== "once") {
			toast.error(
				"Only non-recurring tasks can be rescheduled via drag & drop for now."
			)
			return
		}

		const originalTime = taskItem.schedule.run_at
			? new Date(taskItem.schedule.run_at).toTimeString().split(" ")[0]
			: "12:00:00"
		const newRunAt = new Date(newDate)
		const [hours, minutes, seconds] = originalTime.split(":")
		newRunAt.setHours(hours, minutes, seconds)

		const updatedTask = {
			taskId: taskItem.id,
			schedule: {
				...taskItem.schedule,
				run_at: newRunAt.toISOString()
			}
		}

		toast.loading("Rescheduling task...", { id: "drop-task" })
		try {
			const res = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(updatedTask)
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.error || "Update failed")
			}
			toast.success("Task rescheduled!", { id: "drop-task" })
			fetchData()
		} catch (error) {
			toast.error(`Error: ${error.message}`, { id: "drop-task" })
		}
	}

	// --- Task Action Handlers ---
	const handleApproveTask = async (taskId) => {
		toast.loading("Approving...", { id: "approve-task" })
		try {
			const res = await fetch("/api/tasks/approve", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.error || "Approval failed")
			}
			toast.success("Task approved!", { id: "approve-task" })
			fetchData()
			setViewingTask(null)
		} catch (error) {
			toast.error(`Error: ${error.message}`, { id: "approve-task" })
		}
	}

	const handleDeleteTask = async (taskId) => {
		if (
			!window.confirm(
				"Are you sure you want to delete this task? This may delete recurring instances too."
			)
		) {
			return
		}
		toast.loading("Deleting...", { id: "delete-task" })
		try {
			const res = await fetch("/api/tasks/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.error || "Delete failed")
			}
			toast.success("Task deleted.", { id: "delete-task" })
			fetchData()
			setViewingTask(null)
		} catch (error) {
			toast.error(`Error: ${error.message}`, { id: "delete-task" })
		}
	}

	const handleUpdateTask = async () => {
		if (!editingTask) return
		toast.loading("Updating...", { id: "update-task" })
		try {
			const res = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					...editingTask,
					taskId: editingTask.task_id
				})
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.error)
			}
			toast.success("Task updated!", { id: "update-task" })
			setEditingTask(null)
			fetchData()
		} catch (error) {
			toast.error(`Error: ${error.message}`, { id: "update-task" })
		}
	}

	const handleAnswerClarifications = async (taskId, answers) => {
		toast.loading("Submitting...", { id: "answer-clarification" })
		try {
			const res = await fetch("/api/tasks/answer-clarifications", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId, answers })
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.detail || "Failed to submit answers")
			}
			toast.success("Answers submitted. I'll continue planning.", {
				id: "answer-clarification"
			})
			fetchData()
		} catch (error) {
			toast.error(`Error: ${error.message}`, {
				id: "answer-clarification"
			})
		}
	}

	const handleRerunTask = async (taskId) => {
		toast.loading("Duplicating...", { id: "rerun-task" })
		try {
			const response = await fetch("/api/tasks/rerun", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "Failed to duplicate task.")
			}
			toast.success(
				"Task duplicated. It will appear for approval shortly.",
				{ id: "rerun-task" }
			)
			fetchData()
		} catch (error) {
			toast.error(error.message, { id: "rerun-task" })
		}
	}

	const handleToggleEnableTask = async (taskId, currentEnabledState) => {
		toast.loading(`Toggling...`, { id: "toggle-task" })
		try {
			const response = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId, enabled: !currentEnabledState })
			})
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "Failed to update task")
			}
			toast.success(
				`Task ${currentEnabledState ? "disabled" : "enabled"}!`,
				{ id: "toggle-task" }
			)
			fetchData()
		} catch (error) {
			toast.error(`Error toggling task: ${error.message}`, {
				id: "toggle-task"
			})
		}
	}

	const handleKeyDown = useCallback(
		(e) => {
			if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
				onDayChange(e.key === "ArrowRight" ? 1 : -1)
				e.preventDefault()
			}
			if (e.key === "Escape") {
				setViewingTask(null)
				setEditingTask(null)
				setIsAddingTask(false)
			}
		},
		[onDayChange]
	)

	useEffect(() => {
		window.addEventListener("keydown", handleKeyDown)
		return () => window.removeEventListener("keydown", handleKeyDown)
	}, [handleKeyDown])

	const tasksByDate = useMemo(() => {
		const grouped = {}
		const weekDays = [
			"Sunday",
			"Monday",
			"Tuesday",
			"Wednesday",
			"Thursday",
			"Friday",
			"Saturday"
		]
		const visibleDays = eachDayOfInterval({
			start: subDays(startOfToday(), 365),
			end: addDays(startOfToday(), 365)
		})

		visibleDays.forEach((date) => {
			const dateString = format(date, "yyyy-MM-dd")
			grouped[dateString] = (allTasks || []).filter((task) => {
				const schedule = task.schedule
				if (!schedule) return false
				if (schedule.type === "once" && schedule.run_at) {
					return isSameDay(parseISO(schedule.run_at), date)
				}
				if (schedule.type === "recurring") {
					if (schedule.frequency === "daily") return true
					if (schedule.frequency === "weekly") {
						return schedule.days?.includes(weekDays[getDay(date)])
					}
				}
				return false
			})
		})
		return grouped
	}, [allTasks])
	return (
		<div className="flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] overflow-hidden pl-0 md:pl-20">
			<Tooltip id="tasks-tooltip" style={{ zIndex: 9999 }} />
			<Tooltip id="tasks-help" style={{ zIndex: 9999 }} />

			<div className="absolute top-6 right-6 z-40">
				<button
					data-tooltip-id="tasks-help"
					data-tooltip-content="This is your task Kanban. Drag and drop tasks, manage schedules, and see your week at a glance."
					className="p-1.5 rounded-full text-neutral-500 hover:text-white hover:bg-[var(--color-primary-surface)] pulse-glow-animation"
				>
					<IconHelpCircle size={22} />
				</button>
			</div>

			<div className="flex-1 flex flex-col overflow-hidden">
				<TasksHeader
					viewDate={viewDate}
					onWeekChange={onWeekChange}
					onDayChange={onDayChange}
					onToday={() => setViewDate(startOfToday())}
				/>
				<main className="flex-1 flex overflow-x-auto overflow-y-hidden p-4">
					{isLoading ? (
						<div className="flex justify-center items-center h-full w-full">
							<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
						</div>
					) : (
						<WeeklyKanban
							allTasks={allTasks}
							onViewTask={setViewingTask}
							onEditTask={setEditingTask}
							onDeleteTask={handleDeleteTask}
							onDuplicateTask={handleRerunTask}
							onApproveTask={handleApproveTask}
							onAnswerClarifications={handleAnswerClarifications}
							onToggleEnableTask={handleToggleEnableTask}
							onDataChange={fetchData}
							onTaskDrop={handleTaskDrop}
							viewDate={viewDate}
						/>
					)}
				</main>
			</div>
			<TasksSidebar
				isOpen={isSidebarOpen}
				setIsOpen={setIsSidebarOpen}
				activeTab={activeTab}
				setActiveTab={setActiveTab}
				viewDate={viewDate}
				setViewDate={setViewDate}
				tasksByDate={tasksByDate}
				allTasks={allTasks}
				integrations={integrations}
				onEditTask={setEditingTask}
				onDeleteTask={handleDeleteTask}
				onApproveTask={handleApproveTask}
				onViewTask={setViewingTask}
				onAnswerClarifications={handleAnswerClarifications}
				onToggleEnableTask={handleToggleEnableTask}
				onAddTask={() => setIsAddingTask(true)}
				onDataChange={fetchData}
			/>

			<button
				onClick={() => setIsAddingTask(true)}
				className="absolute bottom-8 right-8 bg-[var(--color-accent-blue)] text-white rounded-full p-4 shadow-lg hover:bg-[var(--color-accent-blue-hover)] transition-transform duration-200 hover:scale-110 z-30"
				data-tooltip-id="tasks-tooltip"
				data-tooltip-content="Add New Task"
			>
				<IconPlus size={24} />
			</button>

			<AnimatePresence>
				{isAddingTask && (
					<AddTaskModal
						onClose={() => setIsAddingTask(false)}
						onTaskAdded={fetchData}
						initialDate={format(viewDate, "yyyy-MM-dd'T'HH:mm")}
					/>
				)}
				{viewingTask && (
					<TaskDetailsModal
						task={viewingTask}
						onClose={() => setViewingTask(null)}
						onApprove={handleApproveTask}
						onDelete={handleDeleteTask}
						onEdit={setEditingTask}
						onAnswerClarification={handleAnswerClarifications}
						onDuplicate={handleRerunTask}
						onToggleEnable={handleToggleEnableTask}
						integrations={integrations}
					/>
				)}
				{editingTask && (
					<EditTaskModal
						task={editingTask}
						onClose={() => setEditingTask(null)}
						onSave={handleUpdateTask}
						setTask={setEditingTask}
						allTools={integrations}
						integrations={integrations}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}
