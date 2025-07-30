"use client"

import React, {
	useState,
	useEffect,
	useCallback,
	Suspense,
	useMemo
} from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { startOfDay, format, isSameDay, getDay, parseISO } from "date-fns"
import { IconLoader, IconX } from "@tabler/icons-react"
import { AnimatePresence, motion } from "framer-motion"
import toast from "react-hot-toast"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"
import { calculateNextRun } from "@utils/taskUtils"

import TaskDetailsPanel from "@components/tasks/TaskDetailsPanel"
import TaskViewSwitcher from "@components/tasks/TaskViewSwitcher"
import ListView from "@components/tasks/ListView"
import CalendarView from "@components/tasks/CalendarView"
import WelcomePanel from "@components/tasks/WelcomePanel"
import CreateTaskInput from "@components/tasks/CreateTaskInput"
import DayDetailView from "@components/tasks/DayDetailView"

function TasksPageContent() {
	const router = useRouter()
	const searchParams = useSearchParams()

	// Raw tasks from API
	const [allTasks, setAllTasks] = useState([])
	// Processed tasks for different views
	const [oneTimeTasks, setOneTimeTasks] = useState([])
	const [recurringTasks, setRecurringTasks] = useState([])
	const [recurringInstances, setRecurringInstances] = useState([])
	const [integrations, setIntegrations] = useState([])
	const [allTools, setAllTools] = useState([])
	const [isLoading, setIsLoading] = useState(true)

	// View control state
	const [view, setView] = useState("list") // 'list' or 'calendar'
	const [rightPanelContent, setRightPanelContent] = useState({
		type: "welcome",
		data: null
	}) // { type: 'welcome' | 'task' | 'day', data: any }
	const [searchQuery, setSearchQuery] = useState("")
	const [createTaskPrompt, setCreateTaskPrompt] = useState("")

	// Sync selectedTask with the main tasks list
	useEffect(() => {
		if (rightPanelContent.type === "task" && rightPanelContent.data) {
			const updatedSelectedTask = allTasks.find(
				(t) => t.task_id === rightPanelContent.data.task_id
			)
			if (updatedSelectedTask) {
				// Preserve instance-specific data like scheduled_date if it exists
				setRightPanelContent({
					type: "task",
					data: { ...rightPanelContent.data, ...updatedSelectedTask }
				})
			} else {
				setRightPanelContent({ type: "welcome", data: null })
			}
		}
	}, [allTasks, rightPanelContent.type, rightPanelContent.data?.task_id]) // eslint-disable-line react-hooks/exhaustive-deps

	const fetchTasks = useCallback(async () => {
		setIsLoading(true)
		try {
			const tasksRes = await fetch("/api/tasks")
			if (!tasksRes.ok) throw new Error("Failed to fetch tasks")
			const tasksData = await tasksRes.json()
			const rawTasks = Array.isArray(tasksData.tasks)
				? tasksData.tasks
				: []
			setAllTasks(rawTasks)

			// --- Process tasks for different views ---
			const oneTime = []
			const recurring = []
			const instances = []
			const today = startOfDay(new Date())

			rawTasks.forEach((task) => {
				if (task.schedule?.type === "recurring") {
					recurring.push(task)
					// Process past runs from `runs` array
					if (task.runs && Array.isArray(task.runs)) {
						task.runs.forEach((run) => {
							const runDate = run.execution_start_time
								? parseISO(run.execution_start_time)
								: null
							if (runDate) {
								instances.push({
									...task,
									status: run.status, // Use the run's specific status
									scheduled_date: runDate,
									instance_id: `${task.task_id}-${run.run_id}`
								})
							}
						})
					}
					// Add next upcoming run
					const nextRunDate = calculateNextRun(
						task.schedule,
						task.created_at,
						task.runs
					)
					if (nextRunDate) {
						instances.push({
							...task,
							status: "active", // Upcoming runs are part of an active workflow
							scheduled_date: nextRunDate,
							instance_id: `${task.task_id}-next`
						})
					}
				} else {
					// One-time tasks
					const scheduledDate = task.schedule?.run_at
						? parseISO(task.schedule.run_at)
						: today
					oneTime.push({
						...task,
						scheduled_date: scheduledDate,
						instance_id: task.task_id
					})
				}
			})

			setOneTimeTasks(oneTime)
			setRecurringTasks(recurring)
			setRecurringInstances(instances)

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
	}, [fetchTasks])

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
				await fetchTasks()
			} catch (error) {
				toast.error(`Error: ${error.message}`, { id: toastId })
			}
		},
		[fetchTasks]
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
	}

	const handleSelectTask = (task) => {
		setRightPanelContent({ type: "task", data: task })
	}

	const handleShowMoreClick = (date) => {
		const tasksForDay = filteredCalendarTasks.filter((task) =>
			isSameDay(task.scheduled_date, date)
		)
		setRightPanelContent({
			type: "day",
			data: { date, tasks: tasksForDay }
		})
	}

	const handleCloseRightPanel = () => {
		setRightPanelContent({ type: "welcome", data: null })
	}

	const handleExampleClick = (prompt) => {
		setCreateTaskPrompt(prompt)
	}

	const handleDayClick = (date) => {
		const formattedDate = format(date, "MMMM do")
		setCreateTaskPrompt(`Create a task for ${formattedDate}: `)
	}

	const filteredOneTimeTasks = useMemo(() => {
		if (!searchQuery.trim()) {
			return oneTimeTasks
		}
		return oneTimeTasks.filter((task) =>
			task.description.toLowerCase().includes(searchQuery.toLowerCase())
		)
	}, [oneTimeTasks, searchQuery])

	const filteredRecurringTasks = useMemo(() => {
		if (!searchQuery.trim()) {
			return recurringTasks
		}
		return recurringTasks.filter((task) =>
			task.description.toLowerCase().includes(searchQuery.toLowerCase())
		)
	}, [recurringTasks, searchQuery])

	const filteredCalendarTasks = useMemo(() => {
		const allCalendarTasks = [...oneTimeTasks, ...recurringInstances]
		if (!searchQuery.trim()) {
			return allCalendarTasks
		}
		return allCalendarTasks.filter((task) =>
			task.description.toLowerCase().includes(searchQuery.toLowerCase())
		)
	}, [oneTimeTasks, recurringInstances, searchQuery])

	return (
		<div className="flex-1 flex h-screen text-white overflow-hidden md:pl-20">
			<Tooltip
				id="tasks-tooltip"
				place="right"
				style={{ zIndex: 9999 }}
			/>
			<div className="flex-1 flex flex-col md:flex-row ml-2 gap-x-2 overflow-hidden">
				{/* Main Content Panel */}
				<main className="flex-1 flex flex-col overflow-hidden relative">
					<div className="absolute -top-[250px] left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-brand-orange/10 rounded-full blur-3xl -z-10" />
					<header className="p-6 flex-shrink-0 flex items-center justify-between bg-transparent">
						<h1 className="text-3xl font-bold text-white">Tasks</h1>
						<div className="absolute top-6 left-1/2 -translate-x-1/2">
							<TaskViewSwitcher view={view} setView={setView} />
						</div>
					</header>

					<div className="flex-1 overflow-y-auto custom-scrollbar">
						{isLoading ? (
							<div className="flex justify-center items-center h-full">
								<IconLoader className="w-8 h-8 animate-spin text-sentient-blue" />
							</div>
						) : (
							<AnimatePresence mode="wait">
								<motion.div
									key={view}
									initial={{ opacity: 0, y: 20 }}
									animate={{ opacity: 1, y: 0 }}
									exit={{ opacity: 0, y: -20 }}
									transition={{ duration: 0.2 }}
									className="h-full"
								>
									{view === "list" ? (
										<ListView
											oneTimeTasks={filteredOneTimeTasks}
											recurringTasks={
												filteredRecurringTasks
											}
											onSelectTask={handleSelectTask}
											searchQuery={searchQuery}
											onSearchChange={setSearchQuery}
										/>
									) : (
										<CalendarView
											tasks={filteredCalendarTasks}
											onSelectTask={handleSelectTask}
											onDayClick={handleDayClick}
											onShowMoreClick={
												handleShowMoreClick
											}
										/>
									)}
								</motion.div>
							</AnimatePresence>
						)}
					</div>

					<CreateTaskInput
						onTaskAdded={fetchTasks}
						prompt={createTaskPrompt}
						setPrompt={setCreateTaskPrompt}
					/>
				</main>

				{/* Right Details Panel */}
				<aside className="w-full md:w-[450px] lg:w-[500px] bg-brand-black border-l border-brand-gray flex-shrink-0 flex flex-col">
					<AnimatePresence mode="wait">
						{rightPanelContent.type === "task" &&
						rightPanelContent.data ? (
							<motion.div
								key={
									rightPanelContent.data.instance_id ||
									rightPanelContent.data.task_id
								}
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								exit={{ opacity: 0 }}
								className="h-full"
							>
								<TaskDetailsPanel
									task={rightPanelContent.data}
									allTools={allTools}
									integrations={integrations}
									onClose={handleCloseRightPanel}
									onSave={handleUpdateTask}
									onDelete={(taskId) =>
										handleAction(
											() =>
												fetch(`/api/tasks/delete`, {
													method: "POST",
													body: JSON.stringify({
														taskId
													}),
													headers: {
														"Content-Type":
															"application/json"
													}
												}),
											"Task deleted."
										)
									}
									onApprove={(taskId) =>
										handleAction(
											() =>
												fetch(`/api/tasks/approve`, {
													method: "POST",
													body: JSON.stringify({
														taskId
													}),
													headers: {
														"Content-Type":
															"application/json"
													}
												}),
											"Task approved."
										)
									}
									onRerun={(taskId) =>
										handleAction(
											() =>
												fetch(`/api/tasks/rerun`, {
													method: "POST",
													body: JSON.stringify({
														taskId
													}),
													headers: {
														"Content-Type":
															"application/json"
													}
												}),
											"Task re-run."
										)
									}
									onAnswerClarifications={(taskId, answers) =>
										handleAction(
											() =>
												fetch(
													`/api/tasks/answer-clarifications`,
													{
														method: "POST",
														body: JSON.stringify({
															taskId,
															answers
														}),
														headers: {
															"Content-Type":
																"application/json"
														}
													}
												),
											"Answers submitted."
										)
									}
									onArchiveTask={(taskId) =>
										handleAction(
											() =>
												fetch(`/api/tasks/update`, {
													method: "POST",
													body: JSON.stringify({
														taskId,
														status: "archived"
													}),
													headers: {
														"Content-Type":
															"application/json"
													}
												}),
											"Task archived."
										)
									}
									onSendChatMessage={(taskId, message) =>
										handleAction(
											() =>
												fetch(`/api/tasks/chat`, {
													method: "POST",
													body: JSON.stringify({
														taskId,
														message
													}),
													headers: {
														"Content-Type":
															"application/json"
													}
												}),
											"Message sent."
										)
									}
								/>
							</motion.div>
						) : rightPanelContent.type === "day" &&
						  rightPanelContent.data ? (
							<motion.div
								key={format(
									rightPanelContent.data.date,
									"yyyy-MM-dd"
								)}
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								exit={{ opacity: 0 }}
								className="h-full"
							>
								<DayDetailView
									date={rightPanelContent.data.date}
									tasks={rightPanelContent.data.tasks}
									onSelectTask={handleSelectTask}
									onClose={handleCloseRightPanel}
								/>
							</motion.div>
						) : (
							<motion.div
								key="welcome"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								exit={{ opacity: 0 }}
								className="h-full"
							>
								<WelcomePanel
									onExampleClick={handleExampleClick}
								/>
							</motion.div>
						)}
					</AnimatePresence>
				</aside>
			</div>
		</div>
	)
}

export default function TasksPage() {
	return (
		<Suspense
			fallback={
				<div className="flex-1 flex h-screen bg-black text-white overflow-hidden justify-center items-center">
					<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
				</div>
			}
		>
			<TasksPageContent />
		</Suspense>
	)
}
