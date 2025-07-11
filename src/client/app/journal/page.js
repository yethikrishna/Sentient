"use client"

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react"
import { useRouter } from "next/navigation"
import toast from "react-hot-toast"
import {
	IconChevronLeft,
	IconChevronRight,
	IconLoader,
	IconX,
	IconCalendar,
	IconPlus,
	IconPencil,
	IconBook,
	IconBrain,
	IconTrash,
	IconSparkles,
	IconChecklist,
	IconCopy,
	IconClock,
	IconGripVertical,
	IconPlugConnected
} from "@tabler/icons-react" // Note: Many more icons will be needed for tasks view
import {
	IconPlayerPlay,
	IconCircleCheck,
	IconMailQuestion,
	IconAlertCircle,
	IconAlertTriangle,
	IconRefresh,
	IconClock as IconClockStatus
} from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"
import { AnimatePresence, motion } from "framer-motion"
import {
	format,
	startOfMonth,
	endOfMonth,
	startOfWeek,
	endOfWeek,
	eachDayOfInterval,
	isSameMonth,
	isSameDay,
	addMonths,
	addDays,
	subDays,
	getDay,
	isToday,
	setHours,
	setMinutes,
	isWithinInterval,
	parseISO
} from "date-fns"
import { useSmoothScroll } from "@hooks/useSmoothScroll"
import { cn } from "@utils/cn"

const weekDays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

const taskStatusColors = {
	pending: {
		icon: IconClockStatus,
		color: "text-gray-400",
		bg: "bg-[var(--color-status-pending)]/80",
		border: "border-[var(--color-status-pending)]"
	},
	processing: {
		icon: IconRefresh,
		color: "text-blue-400",
		bg: "bg-[var(--color-accent-blue)]/80",
		border: "border-[var(--color-accent-blue)]"
	},
	completed: {
		icon: IconCircleCheck,
		color: "text-green-400",
		bg: "bg-[var(--color-accent-green)]/80",
		border: "border-[var(--color-accent-green)]"
	},
	error: {
		icon: IconAlertCircle,
		color: "text-red-400",
		bg: "bg-[var(--color-accent-red)]/80",
		border: "border-[var(--color-accent-red)]"
	},
	approval_pending: {
		icon: IconMailQuestion,
		label: "Pending Approval",
		color: "text-yellow-400",
		bg: "bg-[var(--color-accent-purple)]/80",
		border: "border-[var(--color-accent-purple)]",
		borderColor: "border-yellow-400"
	},
	active: {
		icon: IconPlayerPlay,
		color: "text-green-400",
		bg: "bg-[var(--color-accent-green)]/80",
		border: "border-[var(--color-accent-green)]"
	},
	cancelled: {
		icon: IconX,
		color: "text-gray-500",
		bg: "bg-gray-600/80",
		border: "border-[var(--color-text-muted)]"
	},
	default: {
		icon: IconAlertCircle,
		color: "text-gray-500",
		bg: "bg-gray-500/80",
		border: "border-[var(--color-text-secondary)]"
	}
}

const priorityMap = {
	0: { label: "High", color: "text-red-400" },
	1: { label: "Medium", color: "text-yellow-400" },
	2: { label: "Low", color: "text-gray-400" },
	default: { label: "Medium", color: "text-yellow-400" }
}

const ConnectToolButton = ({ toolName }) => {
	const router = useRouter()
	return (
		<button
			onClick={() => router.push(`/integrations`)}
			className="text-xs self-start bg-yellow-500/20 text-yellow-300 font-semibold py-1 px-2 rounded-full hover:bg-yellow-500/40 transition-colors whitespace-nowrap flex items-center gap-1"
		>
			<IconPlugConnected size={12} />
			Connect {toolName}
		</button>
	)
}

const ScheduleEditor = ({ schedule, setSchedule }) => {
	const handleTypeChange = (type) => {
		const baseSchedule = { ...schedule, type }
		if (type === "once") {
			delete baseSchedule.frequency
			delete baseSchedule.days
			delete baseSchedule.time
		} else {
			delete baseSchedule.run_at
		}
		setSchedule(baseSchedule)
	}

	const handleDayToggle = (day) => {
		const currentDays = schedule.days || []
		const newDays = currentDays.includes(day)
			? currentDays.filter((d) => d !== day)
			: [...currentDays, day]
		setSchedule({ ...schedule, days: newDays })
	}

	return (
		<div className="bg-neutral-800/50 p-4 rounded-lg space-y-4 border border-neutral-700/80 mt-2">
			<div className="flex items-center gap-2">
				{[
					{ label: "Run Once", value: "once" },
					{ label: "Recurring", value: "recurring" }
				].map(({ label, value }) => (
					<button
						key={value}
						onClick={() => handleTypeChange(value)}
						className={cn(
							"px-4 py-1.5 rounded-full text-sm",
							(schedule.type || "once") === value
								? "bg-[var(--color-accent-blue)] text-white"
								: "bg-neutral-600 hover:bg-neutral-500"
						)}
					>
						{label}
					</button>
				))}
			</div>

			{(schedule.type === "once" || !schedule.type) && (
				<div>
					<label className="text-xs text-gray-400 block mb-1">
						Run At (optional, local time)
					</label>
					<input
						type="datetime-local"
						value={schedule.run_at || ""}
						onChange={(e) =>
							setSchedule({ ...schedule, run_at: e.target.value })
						}
						className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
					/>
					<p className="text-xs text-gray-500 mt-1">
						If left blank, the task will run immediately after
						approval.
					</p>
				</div>
			)}

			{schedule.type === "recurring" && (
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label className="text-xs text-gray-400 block mb-1">
							Frequency
						</label>
						<select
							value={schedule.frequency || "daily"}
							onChange={(e) =>
								setSchedule({
									...schedule,
									frequency: e.target.value
								})
							}
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
						>
							<option value="daily">Daily</option>
							<option value="weekly">Weekly</option>
						</select>
					</div>
					<div>
						<label
							className="text-xs text-gray-400 block mb-1"
							data-tooltip-id="tasks-tooltip"
							data-tooltip-content="Tasks are scheduled in Coordinated Universal Time (UTC) to ensure consistency across timezones."
						>
							Time (UTC)
						</label>
						<input
							type="time"
							value={schedule.time || "09:00"}
							onChange={(e) =>
								setSchedule({
									...schedule,
									time: e.target.value
								})
							}
							className="w-full p-2 bg-neutral-600/80 border border-neutral-600 rounded-md focus:border-[var(--color-accent-blue)]"
						/>
					</div>
					{schedule.frequency === "weekly" && (
						<div className="md:col-span-2">
							<label className="text-xs text-gray-400 block mb-2">
								Days
							</label>
							<div className="flex flex-wrap gap-2">
								{[
									"Monday",
									"Tuesday",
									"Wednesday",
									"Thursday",
									"Friday",
									"Saturday",
									"Sunday"
								].map((day) => (
									<button
										key={day}
										onClick={() => handleDayToggle(day)}
										className={cn(
											"px-3 py-1.5 rounded-full text-xs font-semibold",
											(schedule.days || []).includes(day)
												? "bg-[var(--color-accent-blue)] text-white"
												: "bg-neutral-600 hover:bg-neutral-500"
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
// Main Journal Page Component
const OrganizerPage = () => {
	const [viewDate, setViewDate] = useState(new Date())
	const [addingToDay, setAddingToDay] = useState(null)
	const [activeBlock, setActiveBlock] = useState({
		block: null,
		isEditing: false
	})
	const [editingTask, setEditingTask] = useState(null) // For the PlanEditor modal
	const [viewingTask, setViewingTask] = useState(null) // For TaskDetailsModal
	const [deletingBlock, setDeletingBlock] = useState(null)
	const [isPanelOpen, setPanelOpen] = useState(true)
	const [activeTab, setActiveTab] = useState("calendar")
	const [allJournalEntries, setAllJournalEntries] = useState([])
	const [allTasks, setAllTasks] = useState([])
	const [isLoading, setIsLoading] = useState(true) // Combined loading state

	const [integrations, setIntegrations] = useState([]) // For checking connected tools
	const [allTools, setAllTools] = useState([])
	const mainContentRef = useRef(null)
	useSmoothScroll(mainContentRef)

	// MODIFIED: Fetch data for a 3-day view centered on viewDate
	const currentViewStart = useMemo(() => subDays(viewDate, 1), [viewDate])

	// Fetch journal entries and tasks for the current week
	const fetchDataForView = useCallback(async (centerDate) => {
		setIsLoading(true)
		const startDate = format(subDays(centerDate, 1), "yyyy-MM-dd")
		const endDate = format(addDays(centerDate, 1), "yyyy-MM-dd")

		try {
			// Fetch entries for the week, and ALL tasks for the user
			const [entriesRes, tasksRes, integrationsRes] = await Promise.all([
				fetch(`/api/journal?startDate=${startDate}&endDate=${endDate}`),
				fetch("/api/tasks"),
				fetch("/api/settings/integrations")
			])

			if (!entriesRes.ok)
				throw new Error("Failed to fetch journal entries")
			if (!tasksRes.ok) throw new Error("Failed to fetch tasks")
			if (!integrationsRes.ok)
				throw new Error("Failed to fetch integrations")

			const entriesData = await entriesRes.json()
			const tasksData = await tasksRes.json()

			setAllJournalEntries(
				Array.isArray(entriesData.blocks) ? entriesData.blocks : []
			)
			setAllTasks(Array.isArray(tasksData.tasks) ? tasksData.tasks : [])

			const integrationsData = await integrationsRes.json()
			const allIntegrations = integrationsData.integrations || []
			setIntegrations(allIntegrations)
			const tools = allIntegrations.map((i) => ({
				name: i.name,
				display_name: i.display_name
			}))
			setAllTools(tools)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchDataForView(viewDate)

		// Periodically refresh data
		const intervalId = setInterval(() => fetchDataForView(viewDate), 60000)
		return () => clearInterval(intervalId)
	}, [viewDate, fetchDataForView])

	const changeWeek = (amount) => {
		setViewDate((prev) => addDays(prev, amount * 3))
	}
	const changeDay = (amount) => setViewDate((prev) => addDays(prev, amount))

	const journalEntriesByDate = useMemo(() => {
		return allJournalEntries.reduce((acc, entry) => {
			const date = entry.page_date
			if (!acc[date]) {
				acc[date] = []
			}
			acc[date].push(entry)
			return acc
		}, {})
	}, [allJournalEntries])

	const tasksById = useMemo(() => {
		return allTasks.reduce((acc, task) => {
			acc[task.task_id] = task
			return acc
		}, {})
	}, [allTasks])

	const recurringTasksByDate = useMemo(() => {
		if (!allTasks.length) return {}

		const eventsByDate = {}
		const interval = {
			start: subDays(viewDate, 1),
			end: addDays(viewDate, 1)
		}

		allTasks.forEach((task) => {
			if (!task.schedule || task.schedule.type !== "recurring") {
				return
			}
			if (task.enabled === false) return // Skip disabled tasks

			const [hour, minute] = task.schedule.time
				?.split(":")
				.map(Number) || [9, 0]

			eachDayOfInterval(interval).forEach((day) => {
				const dayOfWeek = getDay(day) // Sunday is 0
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
					const dateKey = format(day, "yyyy-MM-dd")
					if (!eventsByDate[dateKey]) {
						eventsByDate[dateKey] = []
					}
					eventsByDate[dateKey].push({
						...task,
						startTime: setMinutes(setHours(day, hour), minute)
					})
				}
			})
		})

		// Sort events within each day by time
		for (const date in eventsByDate) {
			eventsByDate[date].sort((a, b) => a.startTime - b.startTime)
		}

		return eventsByDate
	}, [allTasks, viewDate])

	const refreshData = () => {
		fetchDataForView(viewDate)
	}

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
			refreshData()
		} catch (error) {
			toast.error(`Error approving task: ${error.message}`)
		}
	}

	const handleDeleteTask = async (taskId) => {
		if (
			!taskId ||
			!window.confirm("Are you sure you want to delete this task?")
		)
			return

		try {
			const response = await fetch("/api/tasks/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) throw new Error((await response.json()).error)
			toast.success("Task deleted successfully!")
			refreshData()
		} catch (error) {
			toast.error(`Error deleting task: ${error.message}`)
		}
	}

	const handleUpdateTask = async () => {
		// This will be called from the EditTaskModal
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
			if (!response.ok) throw new Error((await response.json()).error)
			toast.success("Task updated successfully!")
			setEditingTask(null)
			refreshData()
		} catch (error) {
			toast.error(`Failed to update task: ${error.message}`)
		}
	}

	const handleReRunTask = async (taskId) => {
		if (
			!taskId ||
			!window.confirm("Create a new copy of this task to run again?")
		)
			return

		try {
			const response = await fetch("/api/tasks/rerun", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) throw new Error((await response.json()).error)
			toast.success("Task duplicated for approval.")
			refreshData()
		} catch (error) {
			toast.error(`Failed to re-run task: ${error.message}`)
		}
	}

	return (
		<div className="flex h-screen bg-gradient-to-br from-[var(--color-primary-background)] via-[var(--color-primary-background)] to-[var(--color-primary-surface)]/20 text-[var(--color-text-primary)] overflow-x-hidden pl-0 md:pl-20">
			<Tooltip id="journal-tooltip" />
			<div className="flex-1 flex flex-col overflow-hidden h-screen relative">
				<CalendarHeader
					viewDate={viewDate}
					onWeekChange={changeWeek} // This will now change by 3 days
					onDayChange={changeDay}
					onToday={() => setViewDate(new Date())}
				/>
				<main
					ref={mainContentRef}
					className="flex-1 overflow-y-auto p-4 md:p-6 custom-scrollbar"
				>
					{isLoading ? (
						<div className="flex justify-center items-center h-full">
							<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
						</div>
					) : (
						<WeeklyKanban
							viewDate={viewDate} // This will be used by DayColumn for visibility on mobile
							entriesByDate={journalEntriesByDate}
							recurringTasksByDate={recurringTasksByDate}
							tasksById={tasksById}
							addingToDay={addingToDay}
							setAddingToDay={setAddingToDay}
							onViewEntry={(block) =>
								setActiveBlock({ block, isEditing: false })
							}
							onEditEntry={(block) =>
								setActiveBlock({ block, isEditing: true })
							}
							onDeleteEntry={(block) => setDeletingBlock(block)}
							onDuplicateEntry={handleReRunTask}
							onDataChange={refreshData}
						/>
					)}
				</main>
			</div>
			<RightSidebar
				isOpen={isPanelOpen}
				setIsOpen={setPanelOpen}
				activeTab={activeTab}
				setActiveTab={setActiveTab}
				viewDate={viewDate}
				setViewDate={setViewDate}
				journalEntriesByDate={journalEntriesByDate}
				recurringTasksByDate={recurringTasksByDate}
				allTasks={allTasks}
				integrations={integrations}
				onEditTask={setEditingTask}
				onDeleteTask={handleDeleteTask}
				onApproveTask={handleApproveTask}
				onViewTask={(task) => setViewingTask(task)}
			/>
			<AnimatePresence>
				{editingTask && (
					<EditTaskModal
						key={editingTask.task_id}
						task={editingTask}
						onClose={() => setEditingTask(null)}
						onSave={handleUpdateTask}
						setTask={setEditingTask} // This is the 'setEditingTask' state setter
						allTools={allTools}
						integrations={integrations}
					/>
				)}
				{activeBlock.block && (
					<EntryDetailsModal
						key={activeBlock.block.block_id}
						block={activeBlock.block}
						tasksById={tasksById}
						startInEditMode={activeBlock.isEditing}
						onClose={() =>
							setActiveBlock({ block: null, isEditing: false })
						}
						onDataChange={refreshData}
						onDeleteRequest={(block) => setDeletingBlock(block)}
					/>
				)}
				{viewingTask && (
					<TaskDetailsModal
						task={viewingTask}
						onClose={() => setViewingTask(null)}
						onDataChange={refreshData}
						onDeleteRequest={(block) => setDeletingBlock(block)}
					/>
				)}
				{deletingBlock && (
					<DeleteConfirmationModal
						block={deletingBlock}
						onClose={() => setDeletingBlock(null)}
						onDataChange={refreshData}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}

const CalendarHeader = ({
	viewDate,
	onWeekChange,
	onDayChange,
	onToday,
	onCalendarOpen,
	isAdding,
	onStartAdd
}) => {
	const viewStart = subDays(viewDate, 1)
	const viewEnd = addDays(viewDate, 1)
	return (
		<motion.header
			initial={{ y: -20, opacity: 0 }}
			animate={{ y: 0, opacity: 1 }}
			transition={{ duration: 0.6, ease: "easeOut" }}
			className="flex items-center justify-between p-4 md:p-6 border-b border-[var(--color-primary-surface)]/50 backdrop-blur-md bg-[var(--color-primary-background)]/90 shrink-0"
		>
			<motion.div // eslint-disable-line
				className="flex items-center gap-4"
				whileHover={{ scale: 1.02 }}
				transition={{ type: "spring", stiffness: 400, damping: 17 }}
			>
				<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)] flex items-center gap-3">
					Organizer
				</h1>
			</motion.div>
			<div className="flex items-center gap-2 md:gap-6">
				<motion.button // eslint-disable-line
					onClick={onToday}
					whileHover={{ scale: 1.05, y: -2 }}
					whileTap={{ scale: 0.95 }}
					className="xs:hidden md:flex px-4 md:px-6 py-2 text-sm font-medium border border-[var(--color-primary-surface-elevated)] rounded-xl hover:bg-[var(--color-primary-surface)] hover:border-[var(--color-accent-blue)]/30 transition-all duration-300 backdrop-blur-sm"
				>
					Today
				</motion.button>
				{/* Desktop Week Navigator */}
				<div className="hidden md:flex items-center bg-[var(--color-primary-surface)]/50 rounded-2xl p-1 backdrop-blur-sm">
					<button
						onClick={() => onWeekChange(-1)}
						className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95"
					>
						<IconChevronLeft size={18} />
					</button>
					<motion.h2
						key={format(viewStart, "yyyy-MM-dd")}
						initial={{ opacity: 0, y: 10 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ duration: 0.3 }}
						className="w-64 text-center text-lg font-semibold px-4"
					>
						{format(viewStart, "MMMM d")} -{" "}
						{format(viewEnd, "d, yyyy")}
					</motion.h2>
					<button
						onClick={() => onWeekChange(1)}
						className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95"
					>
						<IconChevronRight size={18} />
					</button>
				</div>
				{/* Mobile Day Navigator */}
				<div className="flex items-center bg-[var(--color-primary-surface)]/50 rounded-2xl p-1 backdrop-blur-sm">
					<div className="md:hidden flex items-center">
						<button
							onClick={() => onDayChange(-1)}
							className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95"
						>
							<IconChevronLeft size={18} />
						</button>
						<motion.h2
							key={format(viewDate, "yyyy-MM-dd")}
							initial={{ opacity: 0, y: 10 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.3 }}
							className="w-32 text-center text-base font-semibold px-2"
						>
							{format(viewDate, "MMMM d, yyyy")}
						</motion.h2>
						<button
							onClick={() => onDayChange(1)}
							className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95"
						>
							<IconChevronRight size={18} />
						</button>
					</div>
				</div>
			</div>
		</motion.header>
	)
}

// Weekly Kanban Board Component
const WeeklyKanban = ({
	viewDate,
	entriesByDate,
	recurringTasksByDate,
	addingToDay,
	setAddingToDay,
	onViewEntry,
	onEditEntry,
	onDeleteEntry,
	onDuplicateEntry,
	tasksById,
	onDataChange
}) => {
	const days = useMemo(
		() => [subDays(viewDate, 1), viewDate, addDays(viewDate, 1)],
		[viewDate]
	)

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			transition={{ duration: 0.5, delay: 0.1 }}
			className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1 h-full"
		>
			{days.map((day) => (
				<div
					key={format(day, "yyyy-MM-dd")}
					className={cn(
						"h-full",
						format(day, "yyyy-MM-dd") !==
							format(viewDate, "yyyy-MM-dd") && "hidden md:block"
					)}
				>
					<DayColumn
						day={day}
						journalEntries={
							entriesByDate[format(day, "yyyy-MM-dd")] || []
						}
						recurringTasks={
							recurringTasksByDate[format(day, "yyyy-MM-dd")] ||
							[]
						}
						tasksById={tasksById}
						isAdding={addingToDay === format(day, "yyyy-MM-dd")}
						onStartAdd={() =>
							setAddingToDay(format(day, "yyyy-MM-dd"))
						}
						onEndAdd={() => {
							setAddingToDay(null)
							onDataChange()
						}}
						onViewEntry={onViewEntry}
						onEditEntry={onEditEntry}
						onDeleteEntry={onDeleteEntry}
						onDuplicateEntry={onDuplicateEntry}
					/>
				</div>
			))}
		</motion.div>
	)
}

const DayColumn = ({
	day,
	journalEntries,
	recurringTasks,
	isAdding,
	onStartAdd,
	onEndAdd,
	onViewEntry,
	onEditEntry,
	onDeleteEntry,
	onDuplicateEntry,
	tasksById
}) => {
	const isCurrentDay = isToday(day)
	const isYesterday = isSameDay(day, subDays(new Date(), 1))
	const isTomorrow = isSameDay(day, addDays(new Date(), 1))

	const dayLabel = useMemo(() => {
		if (isCurrentDay) return "Today"
		if (isYesterday) return "Yesterday"
		if (isTomorrow) return "Tomorrow"
		return format(day, "eee")
	}, [day, isCurrentDay, isYesterday, isTomorrow])

	return (
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			transition={{ duration: 0.4, ease: "easeOut" }}
			className="flex flex-col bg-[var(--color-primary-surface)]/20 rounded-2xl h-full"
		>
			<div className="flex justify-between items-center p-4 border-b border-[var(--color-primary-surface)]/50">
				<h3 className="font-semibold text-lg flex items-center gap-2">
					<span
						className={cn(
							isCurrentDay && "text-[var(--color-accent-blue)]"
						)}
					>
						{dayLabel}
					</span>
					<span
						className={cn(
							"text-lg font-bold text-neutral-400",
							isCurrentDay && "text-white"
						)}
					>
						{format(day, "d MMM")}
					</span>
				</h3>
			</div>
			<div className="p-3 space-y-3 flex-1 overflow-y-auto custom-scrollbar">
				{recurringTasks.map((task, index) => (
					<TaskCard
						key={`task-${task.task_id}-${index}`}
						item={{
							...task,
							content: task.description,
							type: "task"
						}}
						onViewEntry={() =>
							toast.error(
								"Recurring task details view not implemented yet."
							)
						}
					/>
				))}
				{journalEntries.map((entry) => (
					<JournalEntryCard
						key={`journal-${entry.block_id}`}
						item={{ ...entry, type: "journal" }}
						linkedTask={tasksById[entry.linked_task_id]}
						onViewEntry={onViewEntry}
						onEditEntry={onEditEntry}
						onDeleteEntry={onDeleteEntry}
						onDuplicateEntry={onDuplicateEntry}
					/>
				))}
				{recurringTasks.length === 0 && journalEntries.length === 0 && (
					<div className="text-center py-10 text-sm text-[var(--color-text-muted)]">
						No entries.
					</div>
				)}
			</div>
			<div className="p-3 mt-auto border-t border-[var(--color-primary-surface)]/50">
				{isAdding ? (
					<InlineAddEntry
						day={day}
						onSave={onEndAdd}
						onCancel={() => onEndAdd()}
					/>
				) : (
					<button
						onClick={onStartAdd}
						className="w-full flex items-center justify-center gap-2 p-3 rounded-lg text-neutral-400 hover:bg-[var(--color-primary-surface)] hover:text-white transition-colors"
					>
						<IconPlus size={18} />
						<span className="text-sm font-medium">Add a card</span>
					</button>
				)}
			</div>
		</motion.div>
	)
}

const InlineAddEntry = ({ day, onSave, onCancel }) => {
	const [content, setContent] = useState("")
	const [isSubmitting, setIsSubmitting] = useState(false)
	const [schedule, setSchedule] = useState({ type: "once", run_at: null })
	const [isScheduleOpen, setScheduleOpen] = useState(false)
	const textareaRef = useRef(null)

	useEffect(() => {
		textareaRef.current?.focus()
	}, [])

	const handleSave = async () => {
		if (!content.trim()) return
		setIsSubmitting(true)
		try {
			const isScheduled =
				schedule.type === "recurring" ||
				(schedule.type === "once" && schedule.run_at)

			if (isScheduled) {
				// 1. Generate plan
				const planResponse = await fetch("/api/tasks/generate-plan", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ prompt: content })
				})
				const planData = await planResponse.json()
				if (!planResponse.ok)
					throw new Error(
						planData.detail || "Failed to generate plan"
					)

				// 2. Add task
				const taskData = {
					description: planData.description || content,
					priority: 1, // default priority
					plan: planData.plan,
					schedule: schedule
				}
				const addTaskResponse = await fetch("/api/tasks/add", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(taskData)
				})
				if (!addTaskResponse.ok)
					throw new Error(
						(await addTaskResponse.json()).error ||
							"Failed to create scheduled task."
					)

				toast.success("Scheduled task created for approval!")
			} else {
				const response = await fetch("/api/journal", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						content: content,
						page_date: format(day, "yyyy-MM-dd"),
						order: 0,
						processWithAI: true // Process as a potential task
					})
				})
				if (!response.ok) throw new Error("Failed to create entry")
				toast.success("Entry saved and sent for processing.")
			}
			onSave()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	return (
		<div className="flex flex-col">
			<textarea
				ref={textareaRef}
				value={content}
				onChange={(e) => setContent(e.target.value)}
				placeholder="Type anything or describe a task to schedule..."
				className="w-full bg-transparent p-2 rounded-md resize-none focus:outline-none placeholder:text-neutral-500 text-sm"
				rows={3}
			></textarea>
			{isScheduleOpen && (
				<ScheduleEditor schedule={schedule} setSchedule={setSchedule} />
			)}
			<div className="flex justify-between items-center mt-2">
				<div className="flex gap-2">
					<button
						onClick={() => setScheduleOpen(!isScheduleOpen)}
						className="p-1.5 rounded-lg text-neutral-400 hover:bg-[var(--color-primary-surface)] hover:text-white transition-colors"
						data-tooltip-id="journal-tooltip"
						data-tooltip-content="Schedule or make recurring"
					>
						<IconClock size={16} />
					</button>
				</div>
				<div className="flex justify-end gap-2">
					<button
						onClick={onCancel}
						className="px-3 py-1 text-xs rounded-md hover:bg-[var(--color-primary-surface-elevated)]"
					>
						Cancel
					</button>
					<button
						onClick={handleSave}
						disabled={isSubmitting || !content.trim()}
						className="px-4 py-1 text-xs font-semibold bg-[var(--color-accent-blue)] text-white rounded-md disabled:opacity-50"
					>
						{isSubmitting ? "Saving..." : "Save"}
					</button>
				</div>
			</div>
		</div>
	)
}

const JournalEntryCard = ({
	item,
	linkedTask,
	onViewEntry,
	onEditEntry,
	onDeleteEntry,
	onDuplicateEntry
}) => {
	const taskStatus = linkedTask?.status
	const statusInfo = taskStatus
		? taskStatusColors[taskStatus] || taskStatusColors.default
		: null

	return (
		<motion.div
			layout
			initial={{ opacity: 0, x: -10 }}
			animate={{ opacity: 1, x: 0 }}
			whileHover={{
				y: -3,
				scale: 1.02,
				boxShadow:
					"0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
			}}
			onClick={() => onViewEntry(item)}
			className={cn(
				"bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-3 rounded-lg border cursor-pointer backdrop-blur-sm shadow-sm group",
				statusInfo
					? `border-l-4 ${statusInfo.border}`
					: "border-transparent"
			)}
		>
			<p className="text-sm leading-relaxed whitespace-pre-wrap">
				{item.content}
			</p>
			<div className="flex items-end justify-between mt-2 pt-2 border-t border-white/5 min-h-[28px]">
				<div>
					{taskStatus && (
						<div className="text-xs font-semibold text-gray-400 capitalize flex items-center gap-1.5">
							<IconSparkles size={12} />
							<span>Task: {taskStatus.replace("_", " ")}</span>
						</div>
					)}
				</div>
				<div className="relative flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
					{item.linked_task_id && (
						<motion.button
							whileHover={{ scale: 1.1, zIndex: 10 }}
							whileTap={{ scale: 0.9 }}
							onClick={(e) => {
								e.stopPropagation()
								onDuplicateEntry(item.linked_task_id)
							}}
							className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-white hover:bg-[var(--color-primary-surface)] transition-all"
							data-tooltip-id="journal-tooltip"
							data-tooltip-content="Duplicate Task"
						>
							<IconCopy size={14} />
						</motion.button>
					)}
					<motion.button
						whileHover={{ scale: 1.1, zIndex: 10 }}
						whileTap={{ scale: 0.9 }}
						onClick={(e) => {
							e.stopPropagation()
							onEditEntry(item)
						}}
						className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-white hover:bg-[var(--color-primary-surface)] transition-all"
						data-tooltip-id="journal-tooltip"
						data-tooltip-content="Edit"
					>
						<IconPencil size={14} />
					</motion.button>
					<motion.button
						whileHover={{ scale: 1.1, zIndex: 10 }}
						whileTap={{ scale: 0.9 }}
						onClick={(e) => {
							e.stopPropagation()
							onDeleteEntry(item)
						}}
						className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-accent-red)] hover:bg-[var(--color-accent-red)]/10 transition-all"
						data-tooltip-id="journal-tooltip"
						data-tooltip-content="Delete"
					>
						<IconTrash size={14} />
					</motion.button>
				</div>
			</div>
		</motion.div>
	)
}

const TaskCard = ({ item, onViewEntry }) => {
	const statusInfo = taskStatusColors[item.status] || taskStatusColors.default

	return (
		<motion.div
			layout
			initial={{ opacity: 0, x: -10 }}
			animate={{ opacity: 1, x: 0 }}
			onClick={() => onViewEntry(item)}
			className="bg-gradient-to-br from-[var(--color-primary-background)]/50 to-[var(--color-primary-surface)]/20 p-3 rounded-lg cursor-pointer group flex items-start gap-3"
		>
			<div className="flex items-center gap-3 flex-grow">
				<IconBrain size={16} className="text-neutral-500" />
				<div className="flex-grow">
					<p className="text-sm font-medium">{item.content}</p>
					<p className="text-xs text-neutral-400">
						{format(item.startTime, "h:mm a")}
					</p>
				</div>
			</div>
			{item.status && (
				<div className="text-xs font-semibold capitalize flex items-center gap-1.5">
					<span
						className={`w-2 h-2 rounded-full ${statusInfo.bg}`}
					></span>
					<span className="text-neutral-400">
						{item.status.replace("_", " ")}
					</span>
				</div>
			)}
		</motion.div>
	)
}

// Right Side Calendar Picker Component
const RightSideCalendar = ({
	viewDate,
	onDateChange,
	entriesByDate,
	recurringTasksByDate
}) => {
	const [pickerMonth, setPickerMonth] = useState(startOfMonth(viewDate))

	useEffect(() => {
		if (!isSameMonth(viewDate, pickerMonth)) {
			setPickerMonth(startOfMonth(viewDate))
		}
	}, [viewDate, pickerMonth])

	const changePickerMonth = (amount) =>
		setPickerMonth((prev) => addMonths(prev, amount))

	const monthStart = startOfMonth(pickerMonth)
	const monthEnd = endOfMonth(pickerMonth)
	const daysInMonth = eachDayOfInterval({
		start: startOfWeek(monthStart),
		end: endOfWeek(monthEnd)
	})
	const weekStart = startOfWeek(viewDate, { weekStartsOn: 0 })
	const weekEnd = endOfWeek(viewDate, { weekStartsOn: 0 })

	return (
		<div className="flex flex-col h-full">
			<div className="flex items-center justify-between mb-4">
				<h3 className="text-xl font-bold">
					{format(pickerMonth, "MMMM yyyy")}
				</h3>
				<div className="flex gap-1">
					<button
						onClick={() => changePickerMonth(-1)}
						className="p-2 rounded-lg hover:bg-[var(--color-primary-surface)]"
					>
						<IconChevronLeft size={16} />
					</button>
					<button
						onClick={() => changePickerMonth(1)}
						className="p-2 rounded-lg hover:bg-[var(--color-primary-surface)]"
					>
						<IconChevronRight size={16} />
					</button>
				</div>
			</div>
			<div className="grid grid-cols-7 gap-y-2 text-center text-sm text-[var(--color-text-muted)] mb-3">
				{weekDays.map((day) => (
					<div key={day}>{day}</div>
				))}
			</div>
			<div className="grid grid-cols-7 gap-1">
				{daysInMonth.map((day) => {
					const isSelectedWeek = isWithinInterval(day, {
						start: weekStart,
						end: weekEnd
					})
					const hasEntry =
						!!entriesByDate[format(day, "yyyy-MM-dd")] ||
						!!recurringTasksByDate[format(day, "yyyy-MM-dd")]
					return (
						<button
							key={format(day, "yyyy-MM-dd")}
							onClick={() => onDateChange(day)}
							className={cn(
								"h-10 w-10 flex items-center justify-center rounded-full transition-colors relative",
								!isSameMonth(day, pickerMonth) &&
									"text-[var(--color-text-muted)]",
								isToday(day) &&
									"ring-2 ring-[var(--color-accent-blue)]",
								isSelectedWeek &&
									"bg-[var(--color-accent-blue)]/20 text-white",
								"hover:bg-[var(--color-primary-surface)]"
							)}
						>
							{format(day, "d")}
							{hasEntry && (
								<span className="absolute bottom-1.5 h-1 w-1 bg-[var(--color-accent-purple)] rounded-full"></span>
							)}
						</button>
					)
				})}
			</div>
			<div className="mt-auto pt-6 text-sm text-gray-500">
				<p className="font-semibold text-gray-400 mb-2">Legend:</p>
				<div className="flex items-center gap-2 mb-1">
					<span className="h-2 w-2 rounded-full bg-[var(--color-accent-purple)]"></span>{" "}
					Has Entries
				</div>
				<div className="flex items-center gap-2 mb-1">
					<span className="h-4 w-4 rounded-full border-2 border-dashed border-[var(--color-accent-blue)] flex items-center justify-center">
						<span className="h-2 w-2"></span>
					</span>{" "}
					Today
				</div>
				<div className="flex items-center gap-2">
					<span className="h-4 w-4 rounded-full bg-[var(--color-accent-blue)]/20"></span>{" "}
					Selected Week
				</div>
			</div>
		</div>
	)
}

const VerticalTabButton = ({ label, icon, isActive, onClick }) => (
	<button
		onClick={onClick}
		className={cn(
			"p-2 rounded-lg transition-colors w-full flex flex-col items-center",
			isActive
				? "bg-blue-500/30"
				: "hover:bg-[var(--color-primary-surface)]"
		)}
	>
		{icon}
		<span className="[writing-mode:vertical-rl] transform rotate-180 text-sm font-semibold tracking-wider mt-2">
			{label}
		</span>
	</button>
)

const RightSidebar = ({
	isOpen,
	setIsOpen,
	activeTab,
	setActiveTab,
	viewDate,
	setViewDate,
	journalEntriesByDate,
	recurringTasksByDate,
	allTasks,
	integrations,
	onEditTask,
	onDeleteTask,
	onApproveTask,
	onViewTask
}) => {
	const [openSections, setOpenSections] = useState({
		active: true,
		approval_pending: true,
		processing: true,
		completed: true
	})

	const groupedTasks = useMemo(
		() => ({
			active: allTasks.filter((t) => t.status === "active"),
			approval_pending: allTasks.filter(
				(t) => t.status === "approval_pending"
			),
			processing: allTasks.filter((t) =>
				["processing", "pending"].includes(t.status)
			),
			completed: allTasks.filter((t) =>
				["completed", "error", "cancelled"].includes(t.status)
			)
		}),
		[allTasks]
	)

	const toggleSection = (section) =>
		setOpenSections((p) => ({ ...p, [section]: !p[section] }))

	const handleTabClick = (tabName) => {
		if (!isOpen || activeTab !== tabName) {
			setActiveTab(tabName)
			setIsOpen(true)
		} else {
			setIsOpen(false)
		}
	}

	return (
		<motion.aside
			animate={{ width: isOpen ? 350 : 60 }}
			transition={{ type: "spring", stiffness: 400, damping: 30 }}
			className="hidden md:flex flex-col h-screen shrink-0 relative"
		>
			<div className="flex h-full">
				{/* Content Panel */}
				<div className="flex-1 overflow-y-auto custom-scrollbar bg-[var(--color-primary-surface)]/50 backdrop-blur-lg">
					{activeTab === "calendar" && (
						<div className="p-4">
							<RightSideCalendar
								viewDate={viewDate}
								onDateChange={setViewDate}
								entriesByDate={journalEntriesByDate}
								recurringTasksByDate={recurringTasksByDate}
							/>
						</div>
					)}
					{activeTab === "tasks" && (
						<div className="space-y-4 p-4">
							<h2 className="text-xl font-semibold text-center mb-4">
								Tasks Overview
							</h2>
							<CollapsibleSection
								title="Active"
								tasks={groupedTasks.active}
								isOpen={openSections.active}
								toggleOpen={() => toggleSection("active")}
								onEditTask={onEditTask}
								onDeleteTask={onDeleteTask}
							/>
							<CollapsibleSection
								title="Pending Approval"
								tasks={groupedTasks.approval_pending}
								isOpen={openSections.approval_pending}
								toggleOpen={() =>
									toggleSection("approval_pending")
								}
								integrations={integrations}
								onEditTask={onEditTask}
								onDeleteTask={onDeleteTask}
								onApproveTask={onApproveTask}
								onViewDetails={onViewTask}
							/>
							<CollapsibleSection
								title="Processing"
								tasks={groupedTasks.processing}
								isOpen={openSections.processing}
								toggleOpen={() => toggleSection("processing")}
								onEditTask={onEditTask}
								onDeleteTask={onDeleteTask}
							/>
							<CollapsibleSection
								title="Completed"
								tasks={groupedTasks.completed}
								isOpen={openSections.completed}
								toggleOpen={() => toggleSection("completed")}
								onEditTask={onEditTask}
								onDeleteTask={onDeleteTask}
							/>
						</div>
					)}
				</div>

				{/* Vertical Tab Bar */}
				<div className="w-[60px] h-full flex flex-col items-center justify-center gap-6 bg-[var(--color-primary-surface)] border-l border-[var(--color-primary-surface-elevated)]">
					<VerticalTabButton
						label="Calendar"
						icon={<IconCalendar size={24} />}
						isActive={isOpen && activeTab === "calendar"}
						onClick={() => handleTabClick("calendar")}
					/>
					<VerticalTabButton
						label="Tasks"
						icon={<IconChecklist size={24} />}
						isActive={isOpen && activeTab === "tasks"}
						onClick={() => handleTabClick("tasks")}
					/>
				</div>
			</div>
		</motion.aside>
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
	if (!tasks || tasks.length === 0) return null
	return (
		<div>
			<button
				onClick={toggleOpen}
				className="w-full flex justify-between items-center py-2 px-1 text-left hover:bg-[var(--color-primary-surface)]/50 rounded-lg transition-colors"
			>
				<h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
					{title} ({tasks.length})
				</h2>
				<IconChevronLeft
					className={cn(
						"transform transition-transform duration-200",
						isOpen ? "-rotate-90" : "rotate-0"
					)}
				/>
			</button>
			<AnimatePresence>
				{isOpen && (
					<motion.div
						initial={{ height: 0, opacity: 0 }}
						animate={{ height: "auto", opacity: 1 }}
						exit={{ height: 0, opacity: 0 }}
						className="overflow-hidden"
					>
						<div className="space-y-2 pt-2 pb-2">
							{tasks.map((task) => (
								<TaskOverviewCard
									key={task.task_id}
									task={task}
									integrations={integrations}
									{...handlers}
								/>
							))}
						</div>
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	)
}

const TaskOverviewCard = ({
	task,
	onEditTask,
	onDeleteTask,
	onApproveTask,
	integrations,
	onViewDetails
}) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	let missingTools = []
	if (task.status === "approval_pending" && integrations) {
		const requiredTools = new Set(task.plan?.map((step) => step.tool) || [])
		requiredTools.forEach((toolName) => {
			const integration = integrations.find((i) => i.name === toolName)
			if (
				integration &&
				!integration.connected &&
				integration.auth_type !== "builtin"
			) {
				missingTools.push(integration.display_name || toolName)
			}
		})
	}
	return (
		<motion.div
			layout
			onClick={(e) => {
				if (e.target.closest("button")) return
				onViewDetails(task)
			}}
			className={cn(
				"group flex items-center gap-3 bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-2.5 rounded-lg shadow-sm border border-transparent",
				"hover:border-blue-500/30",
				"cursor-pointer"
			)}
		>
			<div className="flex-shrink-0">
				<statusInfo.icon className={cn("h-5 w-5", statusInfo.color)} />
			</div>
			<div className="flex-grow min-w-0">
				<p
					className="font-medium text-white text-sm truncate"
					title={task.description}
				>
					{task.description}
				</p>
				{missingTools.length > 0 && (
					<div
						className="flex items-center gap-1 mt-1 text-yellow-400 text-xs"
						data-tooltip-id={`missing-tools-tooltip-sidebar-${task.task_id}`}
					>
						<IconAlertTriangle size={12} />
						<span>Requires: {missingTools.join(", ")}</span>
						<Tooltip
							id={`missing-tools-tooltip-sidebar-${task.task_id}`}
							content="Please connect these tools in Settings to approve this task."
							place="left"
						/>
					</div>
				)}
			</div>
			<div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
				{task.status === "approval_pending" && (
					<>
						<button
							onClick={() => onApproveTask(task.task_id)}
							className="p-1.5 rounded-md text-green-400 hover:bg-green-400/20 disabled:text-gray-600 disabled:cursor-not-allowed"
							data-tooltip-id="journal-tooltip"
							data-tooltip-content="Approve"
							disabled={missingTools.length > 0}
						>
							<IconCircleCheck size={16} />
						</button>
						<button
							onClick={() => onEditTask(task)}
							className="p-1.5 rounded-md text-orange-400 hover:bg-orange-400/20"
							data-tooltip-id="journal-tooltip"
							data-tooltip-content="Edit"
						>
							<IconPencil size={16} />
						</button>
					</>
				)}
				<button
					onClick={() => onDeleteTask(task.task_id)}
					className="p-1.5 rounded-md text-red-400 hover:bg-red-400/20"
					data-tooltip-id="journal-tooltip"
					data-tooltip-content="Delete"
				>
					<IconTrash size={16} />
				</button>
			</div>
		</motion.div>
	)
}

const PlanEditor = ({
	description,
	setDescription,
	priority,
	setPriority,
	plan,
	setPlan,
	schedule,
	setSchedule,
	allTools,
	integrations
}) => {
	const handleAddStep = () =>
		setPlan([...plan, { tool: "", description: "" }])
	const handleRemoveStep = (index) =>
		setPlan(plan.filter((_, i) => i !== index))
	const handleStepChange = (index, field, value) => {
		const newPlan = [...plan]
		newPlan[index][field] = value
		setPlan(newPlan)
	}

	return (
		<>
			<div>
				<label className="text-sm font-medium text-gray-300 mb-2 block">
					Plan Details
				</label>
				<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
					<input
						type="text"
						placeholder="Describe the overall goal..."
						value={description}
						onChange={(e) => setDescription(e.target.value)}
						className="md:col-span-2 p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg transition-colors focus:border-[var(--color-accent-blue)]"
					/>
					<select
						value={priority}
						onChange={(e) => setPriority(Number(e.target.value))}
						className="p-3 bg-neutral-800/50 border border-neutral-700 rounded-lg appearance-none transition-colors focus:border-[var(--color-accent-blue)]"
					>
						<option value={0}>High Priority</option>
						<option value={1}>Medium Priority</option>
						<option value={2}>Low Priority</option>
					</select>
				</div>
			</div>
			<div className="space-y-3">
				<label className="text-sm font-medium text-gray-300">
					Plan Steps
				</label>
				<AnimatePresence>
					{plan.map((step, index) => (
						<motion.div
							key={index}
							layout
							initial={{ opacity: 0, y: -10 }}
							animate={{ opacity: 1, y: 0 }}
							exit={{ opacity: 0, x: -20 }}
							className="flex items-start gap-2 sm:gap-3"
						>
							<IconGripVertical className="h-5 w-5 text-gray-500 flex-shrink-0" />
							<div className="flex-grow flex flex-col gap-2">
								<div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
									<select
										value={step.tool || ""}
										onChange={(e) =>
											handleStepChange(
												index,
												"tool",
												e.target.value
											)
										}
										className="w-full sm:w-2/5 p-2 bg-neutral-800/50 border border-neutral-700 rounded-md text-sm transition-colors focus:border-[var(--color-accent-blue)]"
									>
										<option value="">
											Select a tool...
										</option>
										{allTools.map((tool) => {
											const isConnected =
												integrations.find(
													(i) => i.name === tool.name
												)?.connected ||
												integrations.find(
													(i) => i.name === tool.name
												)?.auth_type === "builtin"
											return (
												<option
													key={tool.name}
													value={tool.name}
												>
													{tool.display_name}{" "}
													{!isConnected &&
														" (Not Connected)"}
												</option>
											)
										})}
									</select>
									<input
										type="text"
										placeholder="Describe what this step should do..."
										value={step.description}
										onChange={(e) =>
											handleStepChange(
												index,
												"description",
												e.target.value
											)
										}
										className="flex-grow p-2 bg-neutral-800/50 border border-neutral-700 rounded-md text-sm transition-colors focus:border-[var(--color-accent-blue)]"
									/>
									<button
										onClick={() => handleRemoveStep(index)}
										className="p-2 text-[var(--color-accent-red)] hover:bg-neutral-700 rounded-full"
									>
										<IconX className="h-4 w-4" />
									</button>
								</div>
								{!integrations.find((i) => i.name === step.tool)
									?.connected &&
									integrations.find(
										(i) => i.name === step.tool
									)?.auth_type !== "builtin" &&
									step.tool && (
										<ConnectToolButton
											toolName={step.tool}
										/>
									)}
							</div>
						</motion.div>
					))}
				</AnimatePresence>
				<button
					onClick={handleAddStep}
					className="flex items-center gap-1.5 py-1.5 px-3 rounded-full bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-xs"
				>
					<IconPlus className="h-4 w-4" /> Add Step
				</button>
			</div>
			<div>
				<label className="text-sm font-medium text-gray-300 mb-2 block">
					Schedule
				</label>
				<ScheduleEditor schedule={schedule} setSchedule={setSchedule} />
			</div>
		</>
	)
}
const EditTaskModal = ({
	task,
	onClose,
	onSave,
	setTask,
	allTools,
	integrations
}) => {
	const safeSchedule = task.schedule || { type: "once", run_at: null }
	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-3xl border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-6">
					<h3 className="text-xl font-semibold">Edit Task</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-2 space-y-6">
					<PlanEditor
						description={task.description}
						setDescription={(val) =>
							setTask({ ...task, description: val })
						}
						priority={task.priority}
						setPriority={(val) =>
							setTask({ ...task, priority: val })
						}
						plan={task.plan}
						setPlan={(val) => setTask({ ...task, plan: val })}
						schedule={safeSchedule}
						setSchedule={(val) =>
							setTask({ ...task, schedule: val })
						}
						allTools={allTools}
						integrations={integrations}
					/>
				</div>
				<div className="flex justify-end gap-4 mt-6 pt-4 border-t border-neutral-700">
					<button
						onClick={onClose}
						className="py-2.5 px-5 rounded-lg bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-sm"
					>
						Cancel
					</button>
					<button
						onClick={onSave}
						className="py-2.5 px-5 rounded-lg bg-[var(--color-accent-green)] hover:bg-[var(--color-accent-green-hover)] text-sm transition-colors"
					>
						Save Changes
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

const DeleteConfirmationModal = ({ block, onClose, onDataChange }) => {
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleConfirmDelete = async () => {
		setIsSubmitting(true)
		try {
			const response = await fetch(
				`/api/journal?blockId=${block.block_id}`,
				{ method: "DELETE" }
			)
			if (!response.ok) throw new Error("Failed to delete block.")
			toast.success("Entry deleted.")
			onDataChange()
			onClose()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-md border border-[var(--color-primary-surface-elevated)]"
			>
				<h2 className="text-xl font-bold mb-2">Delete Entry?</h2>
				<p className="text-[var(--color-text-muted)] mb-6">
					Are you sure you want to permanently delete this journal
					entry? This action cannot be undone.
				</p>
				<div className="flex justify-end gap-3">
					<button
						onClick={onClose}
						disabled={isSubmitting}
						className="px-4 py-2 text-sm rounded-lg hover:bg-[var(--color-primary-surface-elevated)]"
					>
						Cancel
					</button>
					<button
						onClick={handleConfirmDelete}
						disabled={isSubmitting}
						className="px-6 py-2 text-sm font-medium bg-[var(--color-accent-red)] hover:bg-[var(--color-accent-red-hover)] text-white rounded-xl disabled:opacity-50 shadow-lg shadow-red-500/20 transition-colors"
					>
						{isSubmitting ? "Deleting..." : "Delete"}
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

const TaskDetailsModal = ({ task, onClose }) => {
	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	const { thoughts, finalAnswer, mainContent } =
		task.result && typeof task.result === "string"
			? {
					thoughts: task.result.match(
						/<think>([\s\S]*?)<\/think>/
					)?.[1],
					finalAnswer: task.result.match(
						/<final_answer>([\s\S]*?)<\/final_answer>/
					)?.[1],
					mainContent: task.result
						.replace(/<think>[\s\S]*?<\/think>/g, "")
						.replace(/<final_answer>[\s\S]*?<\/final_answer>/g, "")
				}
			: { thoughts: null, finalAnswer: null, mainContent: task.result }

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<Tooltip id="task-details-tooltip" />
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-3xl border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-6">
					<h3 className="text-2xl font-semibold text-white truncate">
						{task.description}
					</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-2 space-y-6">
					<div className="flex items-center gap-4 text-sm">
						<span className="text-[var(--color-text-secondary)]">
							Status:
						</span>
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
						<div className="w-px h-4 bg-[var(--color-primary-surface-elevated)]"></div>
						<span className="text-[var(--color-text-secondary)]">
							Priority:
						</span>
						<span
							className={cn("font-semibold", priorityInfo.color)}
						>
							{priorityInfo.label}
						</span>
					</div>
					<div>
						<h4 className="text-lg font-semibold text-white mb-3">
							Plan
						</h4>
						<div className="space-y-2">
							{task.plan.map((step, index) => (
								<div
									key={index}
									className="flex items-start gap-3 bg-[var(--color-primary-surface)]/70 p-3 rounded-md"
								>
									<div className="flex-shrink-0 text-[var(--color-accent-blue)] font-bold mt-0.5">
										{index + 1}.
									</div>
									<div>
										<p className="font-semibold text-white">
											{step.tool}
										</p>
										<p className="text-sm text-[var(--color-text-secondary)]">
											{step.description}
										</p>
									</div>
								</div>
							))}
						</div>
					</div>
					{task.progress_updates?.length > 0 && (
						<div>
							<h4 className="text-lg font-semibold text-white mb-4">
								Progress
							</h4>
							<div className="space-y-4">
								{task.progress_updates.map((update, index) => (
									<div key={index} className="flex gap-4">
										<div className="flex flex-col items-center">
											<div className="w-4 h-4 bg-blue-500 rounded-full border-2 border-neutral-800"></div>
											{index <
												task.progress_updates.length -
													1 && (
												<div className="w-0.5 flex-grow bg-[var(--color-primary-surface-elevated)]"></div>
											)}
										</div>
										<div>
											<p className="text-sm text-white -mt-1">
												{update.message}
											</p>
											<p className="text-xs text-[var(--color-text-muted)] mt-1.5">
												{new Date(
													update.timestamp
												).toLocaleString()}
											</p>
										</div>
									</div>
								))}
							</div>
						</div>
					)}
				</div>
			</motion.div>
		</motion.div>
	)
}

// Entry Details Modal Component
const EntryDetailsModal = ({
	block,
	tasksById,
	startInEditMode,
	onClose,
	onDataChange,
	onDeleteRequest
}) => {
	const router = useRouter()
	const linkedTask = useMemo(() => {
		if (!block.linked_task_id) return null
		return tasksById[block.linked_task_id]
	}, [block, tasksById])

	const [editingContent, setEditingContent] = useState(block.content)
	const [isEditing, setIsEditing] = useState(startInEditMode || false)
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleUpdate = async () => {
		if (!editingContent.trim())
			return toast.error("Content cannot be empty.")
		setIsSubmitting(true)
		try {
			const response = await fetch(
				`/api/journal?blockId=${block.block_id}`,
				{
					method: "PUT",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ content: editingContent })
				}
			)
			if (!response.ok) throw new Error("Failed to update entry")
			toast.success("Entry updated and sent for re-processing.")
			setIsEditing(false)
			onDataChange()
			onClose() // Close modal on successful update
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	const handleApproveTask = async () => {
		if (!linkedTask?.task_id) return
		setIsSubmitting(true)
		try {
			const response = await fetch("/api/tasks/approve", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId: linkedTask.task_id })
			})
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.detail || "Approval failed")
			}
			toast.success("Plan approved and queued for execution.")
			onDataChange()
			onClose()
		} catch (error) {
			toast.error(`Error approving task: ${error.message}`)
		} finally {
			setIsSubmitting(false)
		}
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-2xl border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-4 flex-shrink-0">
					<h2 className="text-xl font-bold text-[var(--color-accent-blue)]">
						Journal Entry Details
					</h2>
					<motion.button
						whileHover={{ scale: 1.1, rotate: 90 }}
						whileTap={{ scale: 0.9 }}
						onClick={onClose}
						className="p-1 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
					>
						<IconX size={18} />
					</motion.button>
				</div>

				<div className="overflow-y-auto custom-scrollbar pr-2 space-y-6">
					{/* Journal Content Section */}
					<div className="bg-[var(--color-primary-background)]/50 p-4 rounded-lg">
						<div className="flex justify-between items-center mb-2">
							<h3 className="font-semibold text-lg flex items-center gap-2">
								<IconBook size={18} /> Content
							</h3>
							<div className="flex items-center gap-2">
								<button
									onClick={() => setIsEditing(!isEditing)}
									className="text-xs p-1.5 rounded-md hover:bg-[var(--color-primary-surface)]"
									data-tooltip-id="journal-tooltip"
									data-tooltip-content="Edit"
								>
									{isEditing ? (
										<IconX size={14} />
									) : (
										<IconPencil size={14} />
									)}
								</button>
								<button
									onClick={() => onDeleteRequest(block)}
									className="text-xs p-1.5 rounded-md hover:bg-[var(--color-accent-red)]/20 hover:text-[var(--color-accent-red)]"
									data-tooltip-id="journal-tooltip"
									data-tooltip-content="Delete"
								>
									<IconTrash size={14} />
								</button>
							</div>
						</div>
						{isEditing ? (
							<textarea
								value={editingContent}
								onChange={(e) =>
									setEditingContent(e.target.value)
								}
								className="w-full bg-[var(--color-primary-surface)]/50 p-2 rounded-md"
								rows={5}
							/>
						) : (
							<p className="whitespace-pre-wrap text-[var(--color-text-secondary)] leading-relaxed">
								{block.content}
							</p>
						)}
						{isEditing && (
							<div className="text-right mt-2">
								<button
									onClick={handleUpdate}
									disabled={isSubmitting}
									className="text-xs px-3 py-1 bg-[var(--color-accent-blue)] text-white rounded-md disabled:opacity-50"
								>
									{isSubmitting
										? "Saving..."
										: "Save Changes"}
								</button>
							</div>
						)}
					</div>

					{/* Linked Task Section */}
					{linkedTask && (
						<div className="bg-[var(--color-primary-background)]/50 p-4 rounded-lg">
							<h3
								className="font-semibold text-lg mb-3 flex items-center justify-between gap-2"
								onClick={() => router.push("/tasks")}
							>
								<IconSparkles
									size={18}
									className="text-[var(--color-accent-blue)]"
								/>{" "}
								Linked Task
								<button
									className="text-xs text-[var(--color-accent-blue)] hover:underline"
									onClick={() => router.push("/tasks")}
								>
									View in Tasks
								</button>
							</h3>
							<div className="space-y-4">
								<div>
									<strong className="text-[var(--color-text-secondary)]">
										Description:
									</strong>{" "}
									{linkedTask.description}
								</div>
								<div>
									<strong className="text-[var(--color-text-secondary)]">
										Status:
									</strong>{" "}
									<span className="capitalize font-semibold">
										{linkedTask.status.replace("_", " ")}
									</span>
								</div>

								<div>
									<strong className="text-[var(--color-text-secondary)]">
										Plan:
									</strong>
									<ul className="list-decimal list-inside mt-1 space-y-1 text-sm text-[var(--color-text-secondary)]">
										{linkedTask.plan.map((step, i) => (
											<li key={i}>
												<strong>{step.tool}:</strong>{" "}
												{step.description}
											</li>
										))}
									</ul>
								</div>

								{block.task_progress?.length > 0 && (
									<div>
										<strong className="text-[var(--color-text-secondary)]">
											Progress:
										</strong>
										<ul className="mt-1 space-y-2 text-sm text-[var(--color-text-secondary)]">
											{block.task_progress.map(
												(update, i) => (
													<li
														key={i}
														className="flex gap-2"
													>
														<span className="text-[var(--color-text-muted)]">
															{format(
																parseISO(
																	update.timestamp
																),
																"h:mm a"
															)}
															:
														</span>
														<span>
															{update.message}
														</span>
													</li>
												)
											)}
										</ul>
									</div>
								)}

								{block.task_result && (
									<div>
										<strong className="text-[var(--color-text-secondary)]">
											Outcome:
										</strong>
										<pre className="mt-1 p-3 bg-black/20 rounded-md text-xs whitespace-pre-wrap font-mono">
											{block.task_result}
										</pre>
									</div>
								)}
							</div>
						</div>
					)}
				</div>

				<div className="flex justify-end gap-3 mt-6 flex-shrink-0">
					<button
						onClick={onClose}
						className="px-6 py-2 text-sm rounded-lg hover:bg-[var(--color-primary-surface-elevated)] bg-[var(--color-primary-surface)]"
					>
						Close
					</button>
					{linkedTask?.status === "approval_pending" && (
						<button
							onClick={handleApproveTask}
							disabled={isSubmitting}
							className="px-6 py-2 text-sm font-medium bg-[var(--color-accent-green)] hover:bg-[var(--color-accent-green-hover)] text-white rounded-xl disabled:opacity-50 shadow-lg shadow-[var(--color-accent-green)]/20 transition-colors"
						>
							{isSubmitting ? "Approving..." : "Approve Plan"}
						</button>
					)}
				</div>
			</motion.div>
		</motion.div>
	)
}

export default OrganizerPage
