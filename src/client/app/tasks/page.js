"use client"

import React, {
	useState,
	useEffect,
	useCallback,
	Suspense,
	useMemo
} from "react"
import { useRouter, useSearchParams } from "next/navigation"
import {
	format,
	isSameDay,
	parseISO,
	startOfMonth,
	endOfMonth,
	startOfWeek,
	endOfWeek
} from "date-fns"
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
import GCalEventDetailsPanel from "@components/tasks/GCalEventCardDetailsPanel"
import WelcomePanel from "@components/tasks/WelcomePanel"
import CreateTaskInput from "@components/tasks/CreateTaskInput"
import InteractiveNetworkBackground from "@components/ui/InteractiveNetworkBackground"
import { IconSparkles } from "@tabler/icons-react"
import DayDetailView from "@components/tasks/DayDetailView"

function TasksPageContent() {
	const router = useRouter()
	const searchParams = useSearchParams()

	// Raw tasks from API
	const [allTasks, setAllTasks] = useState([])
	// Processed tasks for different views

	const [integrations, setIntegrations] = useState([])
	const [allTools, setAllTools] = useState([])
	const [isLoading, setIsLoading] = useState(true)

	// View control state
	const [view, setView] = useState("list") // 'list' or 'calendar'
	// MODIFIED: Change initial state to 'initial' to handle client-side screen size check
	const [rightPanelContent, setRightPanelContent] = useState({
		type: "initial",
		data: null
	}) // { type: 'initial' | 'hidden' | 'welcome' | 'task' | 'day', data: any }
	const [gcalEvents, setGcalEvents] = useState([])
	const [isGcalConnected, setIsGcalConnected] = useState(false)
	const [currentCalendarDate, setCurrentCalendarDate] = useState(new Date()) // To track calendar view range
	const [searchQuery, setSearchQuery] = useState("")
	const [createTaskPrompt, setCreateTaskPrompt] = useState("")

	// Processed tasks for different views are derived from allTasks
	const {
		oneTimeTasks,
		recurringTasks,
		triggeredTasks,
		swarmTasks,
		recurringInstances
	} = useMemo(() => {
		const oneTime = []
		const recurring = []
		const triggered = []
		const swarm = []
		const instances = []

		allTasks.forEach((task) => {
			if (task.task_type === "swarm") {
				swarm.push(task)
			} else if (task.schedule?.type === "recurring") {
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
						status: "pending", // An upcoming run is pending
						scheduled_date: nextRunDate,
						instance_id: `${task.task_id}-next`
					})
				}
			} else if (task.schedule?.type === "triggered") {
				triggered.push(task)
			} else {
				// One-time tasks
				const scheduledDate = task.schedule?.run_at
					? parseISO(task.schedule.run_at)
					: parseISO(task.created_at)
				oneTime.push({
					...task,
					scheduled_date: scheduledDate,
					instance_id: task.task_id
				})
			}
		})

		return {
			oneTimeTasks: oneTime,
			recurringTasks: recurring,
			triggeredTasks: triggered,
			swarmTasks: swarm,
			recurringInstances: instances
		}
	}, [allTasks])

	useEffect(() => {
		// On initial client-side load, determine the default panel state.
		// On mobile, the panel is hidden. On desktop, it shows the welcome panel.
		if (rightPanelContent.type === "initial") {
			if (window.innerWidth < 768) {
				setRightPanelContent({ type: "hidden", data: null })
			} else {
				setRightPanelContent({ type: "welcome", data: null })
			}
		}
	}, [rightPanelContent.type])

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
				// If task disappears, hide panel on mobile, show welcome on desktop
				const nextState = window.innerWidth < 768 ? "hidden" : "welcome"
				setRightPanelContent({ type: nextState, data: null })
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
		const gcal = integrations.find((i) => i.name === "gcalendar")
		setIsGcalConnected(gcal?.connected || false)
	}, [integrations])

	// New useEffect for fetching GCal events
	const fetchGcalEvents = useCallback(
		async (date) => {
			if (!isGcalConnected || view !== "calendar") return

			// Calculate the visible date range for the calendar view
			const monthStart = startOfMonth(date)
			const monthEnd = endOfMonth(date)
			const startDate = startOfWeek(monthStart)
			const endDate = endOfWeek(monthEnd)

			try {
				const res = await fetch(
					`/api/integrations/gcalendar/events?start_date=${startDate.toISOString()}&end_date=${endDate.toISOString()}`
				)
				if (!res.ok)
					throw new Error("Failed to fetch Google Calendar events")
				const data = await res.json()

				// Add a type and parse dates
				const formattedEvents = (data.events || []).map((event) => ({
					...event,
					type: "gcal",
					scheduled_date: parseISO(event.start), // Use 'start' from GCal event
					end_date: parseISO(event.end),
					instance_id: `gcal-${event.id}` // Unique ID for React key
				}))
				setGcalEvents(formattedEvents)
			} catch (error) {
				toast.error(error.message)
				setGcalEvents([]) // Clear on error
			}
		},
		[isGcalConnected, view]
	)

	useEffect(() => {
		fetchGcalEvents(currentCalendarDate)
	}, [currentCalendarDate, fetchGcalEvents])

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

	const handleAddTask = (newTask) => {
		// Optimistically add the new task to the state
		setAllTasks((prevTasks) => [...prevTasks, newTask])
	}

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

	const handleSelectItem = (item) => {
		if (item.type === "gcal") {
			setRightPanelContent({ type: "gcal", data: item })
		} else {
			setRightPanelContent({ type: "task", data: item })
		}
	}

	const handleShowMoreClick = (date) => {
		const tasksForDay = filteredCalendarTasks.filter(
			(task) => isSameDay(task.scheduled_date, date) // prettier-ignore
		)
		const eventsForDay = gcalEvents.filter((event) =>
			isSameDay(event.scheduled_date, date)
		)
		const allItemsForDay = [...tasksForDay, ...eventsForDay]
		setRightPanelContent({
			type: "day",
			data: { date, tasks: allItemsForDay }
		})
	}

	const handleCloseRightPanel = () => {
		// On mobile, closing the panel should hide it completely.
		// On desktop, it should revert to the welcome/examples panel.
		const nextState = window.innerWidth < 768 ? "hidden" : "welcome"
		setRightPanelContent({ type: nextState, data: null })
	}

	const handleCreateTaskFromEvent = async (event) => {
		const prompt = `Help me prepare for this event from my calendar:

Title: ${event.summary}
Time: ${event.start} to ${event.end}
Attendees: ${(event.attendees || []).join(", ")}
Description: ${event.description || "No description."}`

		await handleAction(
			() =>
				fetch("/api/tasks/add", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ prompt, assignee: "ai" })
				}),
			"Task created from calendar event!"
		)
		handleCloseRightPanel() // Close the panel after creating the task
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
		return oneTimeTasks.filter(
			(task) =>
				task.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				(task.description &&
					task.description
						.toLowerCase()
						.includes(searchQuery.toLowerCase()))
		)
	}, [oneTimeTasks, searchQuery])

	const filteredActiveWorkflows = useMemo(() => {
		const allWorkflows = [
			...swarmTasks,
			...recurringTasks,
			...triggeredTasks
		]
		if (!searchQuery.trim()) {
			return allWorkflows
		}
		return allWorkflows.filter(
			(task) =>
				task.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				(task.description &&
					task.description
						.toLowerCase()
						.includes(searchQuery.toLowerCase()))
		)
	}, [swarmTasks, recurringTasks, triggeredTasks, searchQuery])

	const filteredCalendarTasks = useMemo(() => {
		const allCalendarTasks = [...oneTimeTasks, ...recurringInstances]
		if (!searchQuery.trim()) {
			return allCalendarTasks
		}
		return allCalendarTasks.filter((task) =>
			(task.name || task.summary)
				?.toLowerCase()
				.includes(searchQuery.toLowerCase())
		)
	}, [oneTimeTasks, recurringInstances, searchQuery])

	const isPanelVisible =
		rightPanelContent.type !== "hidden" &&
		rightPanelContent.type !== "initial"

	return (
		<div className="flex-1 flex h-screen text-white overflow-hidden">
			<Tooltip
				id="tasks-tooltip"
				place="right"
				style={{ zIndex: 9999 }}
			/>
			<div className="flex-1 flex overflow-hidden relative">
				<div className="absolute inset-0 z-[-1] network-grid-background">
					<InteractiveNetworkBackground />
				</div>
				{/* Main Content Panel */}
				<main className="flex-1 flex flex-col overflow-hidden relative">
					<div className="absolute -top-[250px] left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-brand-orange/10 rounded-full blur-3xl -z-10" />
					<header className="p-6 pt-20 md:pt-6 flex-shrink-0 flex items-center justify-between bg-transparent">
						<h1 className="text-3xl font-bold text-white">Tasks</h1>
						<div className="absolute top-6 left-1/2 -translate-x-1/2">
							<TaskViewSwitcher view={view} setView={setView} />
						</div>
						{/* Button to show examples on mobile */}
						<div className="md:hidden">
							<button
								onClick={() =>
									setRightPanelContent({
										type: "welcome",
										data: null
									})
								}
								className="p-2 rounded-full bg-neutral-800/50 hover:bg-neutral-700/80 text-white"
							>
								<IconSparkles size={20} />
							</button>
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
									initial={{ opacity: 0 }}
									animate={{ opacity: 1 }}
									exit={{ opacity: 0 }}
									transition={{ duration: 0.3 }}
									className="h-full"
								>
									{view === "list" ? (
										<ListView
											oneTimeTasks={filteredOneTimeTasks}
											activeWorkflows={
												filteredActiveWorkflows
											}
											onSelectTask={handleSelectItem}
											searchQuery={searchQuery}
											onSearchChange={setSearchQuery}
										/>
									) : (
										<CalendarView
											tasks={filteredCalendarTasks} // prettier-ignore
											gcalEvents={gcalEvents}
											onSelectTask={handleSelectItem}
											onDayClick={handleDayClick}
											onShowMoreClick={
												handleShowMoreClick
											}
											onMonthChange={
												setCurrentCalendarDate
											}
										/>
									)}
								</motion.div>
							</AnimatePresence>
						)}
					</div>

					<CreateTaskInput
						onTaskAdded={handleAddTask}
						prompt={createTaskPrompt}
						setPrompt={setCreateTaskPrompt}
					/>
				</main>

				{/* Right Details Panel */}
				<AnimatePresence>
					{isPanelVisible && (
						<motion.aside
							key="details-panel"
							initial={{ x: "100%" }}
							animate={{ x: "0%" }}
							exit={{ x: "100%" }}
							transition={{
								type: "spring",
								stiffness: 300,
								damping: 30
							}}
							className="fixed inset-0 z-50 bg-brand-black md:relative md:inset-auto md:z-auto md:w-[450px] lg:w-[500px] md:bg-brand-black/50 md:backdrop-blur-sm md:border-l md:border-brand-gray flex-shrink-0 flex flex-col"
						>
							<AnimatePresence mode="wait">
								{rightPanelContent.type === "task" &&
								rightPanelContent.data ? (
									<motion.div
										key={
											rightPanelContent.data
												.instance_id ||
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
														fetch(
															`/api/tasks/delete`,
															{
																method: "POST",
																body: JSON.stringify(
																	{
																		taskId
																	}
																),
																headers: {
																	"Content-Type":
																		"application/json"
																}
															}
														),
													"Task deleted."
												)
											}
											onApprove={(taskId) =>
												handleAction(
													() =>
														fetch(
															`/api/tasks/approve`,
															{
																method: "POST",
																body: JSON.stringify(
																	{
																		taskId
																	}
																),
																headers: {
																	"Content-Type":
																		"application/json"
																}
															}
														),
													"Task approved."
												)
											}
											onRerun={(taskId) =>
												handleAction(
													() =>
														fetch(
															`/api/tasks/answer-clarifications`,
															{
																method: "POST",
																body: JSON.stringify(
																	{
																		taskId,
																		answers
																	}
																),
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
														fetch(
															`/api/tasks/update`,
															{
																method: "POST",
																body: JSON.stringify(
																	{
																		taskId,
																		status: "archived"
																	}
																),
																headers: {
																	"Content-Type":
																		"application/json"
																}
															}
														),
													"Task archived."
												)
											}
											onSendChatMessage={(
												taskId,
												message
											) =>
												handleAction(
													() =>
														fetch(
															`/api/tasks/chat`,
															{
																method: "POST",
																body: JSON.stringify(
																	{
																		taskId,
																		message
																	}
																),
																headers: {
																	"Content-Type":
																		"application/json"
																}
															}
														),
													"Message sent."
												)
											}
										/>
									</motion.div>
								) : rightPanelContent.type === "gcal" &&
								  rightPanelContent.data ? (
									<motion.div
										key={`gcal-${rightPanelContent.data.id}`}
										initial={{ opacity: 0 }}
										animate={{ opacity: 1 }}
										exit={{ opacity: 0 }}
										className="h-full"
									>
										<GCalEventDetailsPanel
											event={rightPanelContent.data}
											onClose={handleCloseRightPanel}
											onCreateTask={
												handleCreateTaskFromEvent
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
											onSelectTask={handleSelectItem}
											onClose={handleCloseRightPanel}
										/>
									</motion.div>
								) : rightPanelContent.type === "welcome" ? (
									<motion.div
										key="welcome"
										initial={{ opacity: 0 }}
										animate={{ opacity: 1 }}
										exit={{ opacity: 0 }}
										className="h-full"
									>
										<WelcomePanel
											onExampleClick={handleExampleClick}
											onClose={handleCloseRightPanel}
										/>
									</motion.div>
								) : null}
							</AnimatePresence>
						</motion.aside>
					)}
				</AnimatePresence>
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
