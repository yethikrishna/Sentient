"use client"

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react"
import toast from "react-hot-toast"
import {
	IconChevronLeft,
	IconChevronRight,
	IconLoader,
	IconX,
	IconSettings,
	IconTrash,
	IconBook,
	IconPencil
} from "@tabler/icons-react"
import { useRouter } from "next/navigation"
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
	addYears,
	isToday,
	setHours,
	setMinutes,
	isWithinInterval,
	parseISO,
	addHours,
	getHours,
	getMinutes
} from "date-fns"
import { useSmoothScroll } from "@hooks/useSmoothScroll"
import { cn } from "@utils/cn"

// Generate a random color for events
const eventColors = [
	"bg-blue-500/80 border-blue-400",
	"bg-green-500/80 border-green-400",
	"bg-purple-500/80 border-purple-400",
	"bg-red-500/80 border-red-400",
	"bg-yellow-500/80 border-yellow-400",
	"bg-indigo-500/80 border-indigo-400",
	"bg-pink-500/80 border-pink-400"
]
const getRandomColor = (id) => {
	// Simple hash function to get a consistent color for the same task
	let hash = 0
	if (!id) return eventColors[0]
	for (let i = 0; i < id.length; i++) {
		hash = id.charCodeAt(i) + ((hash << 5) - hash)
	}
	return eventColors[Math.abs(hash) % eventColors.length]
}

// CalendarHeader component
const CalendarHeader = ({ viewDate, onViewDateChange, onSettingsOpen }) => {
	const changeWeek = (amount) => {
		onViewDateChange((prev) => addDays(prev, amount * 7))
	}

	return (
		<header className="p-4 border-b border-[var(--color-primary-surface)]/50 flex-shrink-0 flex justify-between items-center">
			<div className="flex items-center gap-4">
				<h1 className="text-2xl font-bold">Journal</h1>
				<button
					onClick={() => onViewDateChange(new Date())}
					className="px-4 py-1.5 text-sm font-medium border border-[var(--color-primary-surface-elevated)] rounded-lg hover:bg-[var(--color-primary-surface)] transition-all"
				>
					Today
				</button>
				<div className="flex items-center">
					<button
						onClick={() => changeWeek(-1)}
						className="p-2 rounded-full hover:bg-[var(--color-primary-surface)]"
					>
						<IconChevronLeft size={18} />
					</button>
					<button
						onClick={() => changeWeek(1)}
						className="p-2 rounded-full hover:bg-[var(--color-primary-surface)]"
					>
						<IconChevronRight size={18} />
					</button>
				</div>
				<h2 className="text-xl font-semibold">
					{format(viewDate, "MMMM yyyy")}
				</h2>
			</div>
			<button
				onClick={onSettingsOpen}
				className="p-2 rounded-full hover:bg-[var(--color-primary-surface)]"
			>
				<IconSettings size={20} />
			</button>
		</header>
	)
}

// TaskEvent component
const TaskEvent = ({ event, onTaskClick }) => {
	const startHour = getHours(event.startTime)
	const startMinute = getMinutes(event.startTime)
	const endHour = getHours(event.endTime)
	const endMinute = getMinutes(event.endTime)

	const durationMinutes =
		endHour * 60 + endMinute - (startHour * 60 + startMinute)

	const topRem = ((startHour * 60 + startMinute) / 60) * 6 // 6rem per hour (h-24)
	const heightRem = (durationMinutes / 60) * 6 // 6rem per hour (h-24)

	const colorClass = getRandomColor(event.task_id)

	return (
		<motion.div
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			onClick={() => onTaskClick(event)}
			className={cn(
				"absolute left-1 right-1 p-2 rounded-lg cursor-pointer text-white overflow-hidden text-xs",
				colorClass
			)}
			style={{
				top: `${topRem}rem`,
				height: `${Math.max(heightRem, 2)}rem`
			}}
		>
			<p className="font-bold truncate">{event.description}</p>
			<p>{format(event.startTime, "h:mm a")}</p>
		</motion.div>
	)
}

// CalendarGrid Component
const CalendarGrid = ({ viewDate, events, onDayClick, onTaskClick }) => {
	const weekStart = startOfWeek(viewDate, { weekStartsOn: 0 })
	const days = eachDayOfInterval({
		start: weekStart,
		end: endOfWeek(weekStart)
	})
	const hours = Array.from({ length: 24 }, (_, i) => i)
	const [currentTime, setCurrentTime] = useState(new Date())

	useEffect(() => {
		const timer = setInterval(() => setCurrentTime(new Date()), 60000) // Update every minute
		return () => clearInterval(timer)
	}, [])

	const topPosition =
		(currentTime.getHours() * 60 + currentTime.getMinutes()) / (24 * 60)

	return (
		<div className="flex-grow flex flex-col min-h-0">
			{/* Day Headers */}
			<div className="flex sticky top-0 bg-[var(--color-primary-background)]/80 backdrop-blur-sm z-20">
				<div className="w-16 flex-shrink-0 border-r border-b border-[var(--color-primary-surface)]/50"></div>
				<div className="grid grid-cols-7 flex-grow">
					{days.map((day) => (
						<div
							key={day.toString()}
							className="text-center py-2 border-r border-b border-[var(--color-primary-surface)]/50 flex items-center justify-center gap-1"
						>
							<div
								className="flex flex-col items-center cursor-pointer"
								onClick={() => onDayClick(day)}
							>
								<p className="text-sm text-gray-400">
									{format(day, "eee")}
								</p>
								<p
									className={cn(
										"text-2xl font-bold mt-1",
										isToday(day) && "text-blue-500"
									)}
								>
									{format(day, "d")}
								</p>
							</div>
							<button
								onClick={() => onDayClick(day)}
								className="p-1 rounded-full text-gray-500 hover:text-white hover:bg-[var(--color-primary-surface)]"
							>
								<IconPencil size={14} />
							</button>
						</div>
					))}
				</div>
			</div>
			{/* Grid Content */}
			<div className="flex-grow flex relative">
				<div className="w-16 flex-shrink-0">
					{hours.map((hour) => (
						<div
							key={hour}
							className="h-24 text-right text-xs text-gray-400 pr-2 pt-1 border-r border-t border-[var(--color-primary-surface)]/50"
						>
							{hour === 0
								? ""
								: format(setHours(new Date(), hour), "ha")}
						</div>
					))}
				</div>
				<div className="grid grid-cols-7 flex-grow">
					{days.map((day) => (
						<div
							key={day.toString()}
							className="relative border-r border-[var(--color-primary-surface)]/50"
						>
							{hours.map((hour) => (
								<div
									key={hour}
									className="h-24 border-t border-[var(--color-primary-surface)]/50"
								></div>
							))}
						</div>
					))}
				</div>
				{/* Events Overlay */}
				<div className="absolute top-0 left-16 right-0 bottom-0 grid grid-cols-7">
					{days.map((day) => (
						<div
							key={`events-${day.toString()}`}
							className="relative"
						>
							{events
								.filter((event) =>
									isSameDay(event.startTime, day)
								)
								.map((event) => (
									<TaskEvent
										key={
											event.task_id +
											event.startTime.toISOString()
										}
										event={event}
										onTaskClick={onTaskClick}
									/>
								))}
						</div>
					))}
				</div>
				{/* Current Time Indicator */}
				<div className="absolute top-0 left-16 right-0 bottom-0 pointer-events-none">
					{isWithinInterval(new Date(), {
						start: weekStart,
						end: endOfWeek(weekStart)
					}) && (
						<div
							className="absolute w-full h-0.5 bg-red-500 z-30"
							style={{ top: `${topPosition * 100}%` }}
						>
							<div className="absolute -left-1.5 -top-1 h-3 w-3 bg-red-500 rounded-full"></div>
						</div>
					)}
				</div>
			</div>
		</div>
	)
}

// JournalSidePanel
const JournalSidePanel = ({ selectedDate, entries, onClose, onDataChange }) => {
	const [newEntryContent, setNewEntryContent] = useState("")
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleAddEntry = async () => {
		if (!newEntryContent.trim()) return
		setIsSubmitting(true)
		try {
			const response = await fetch("/api/journal", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					content: newEntryContent,
					page_date: format(selectedDate, "yyyy-MM-dd"),
					order: entries.length,
					processWithAI: true
				})
			})
			if (!response.ok) throw new Error("Failed to add entry")
			toast.success("Entry added.")
			onDataChange()
			setNewEntryContent("")
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	const handleDeleteEntry = async (blockId) => {
		if (!window.confirm("Are you sure you want to delete this entry?"))
			return
		try {
			const response = await fetch(`/api/journal?blockId=${blockId}`, {
				method: "DELETE"
			})
			if (!response.ok) throw new Error("Failed to delete entry")
			toast.success("Entry deleted")
			onDataChange()
		} catch (error) {
			toast.error(error.message)
		}
	}

	return (
		<motion.aside
			initial={{ x: "100%" }}
			animate={{ x: 0 }}
			exit={{ x: "100%" }}
			transition={{ type: "spring", stiffness: 300, damping: 30 }}
			className="fixed top-0 right-0 h-full w-96 bg-[var(--color-primary-background)] border-l border-[var(--color-primary-surface)] p-6 shadow-2xl z-40 flex flex-col"
		>
			<div className="flex justify-between items-center mb-6">
				<h2 className="text-xl font-bold flex items-center gap-2">
					<IconBook />
					Entries for {format(selectedDate, "MMMM d")}
				</h2>
				<button
					onClick={onClose}
					className="p-1 rounded-full hover:bg-[var(--color-primary-surface)]"
				>
					<IconX />
				</button>
			</div>

			<div className="flex-1 overflow-y-auto custom-scrollbar space-y-4 pr-2">
				{entries.length > 0 ? (
					entries.map((entry) => (
						<div
							key={entry.block_id}
							className="bg-[var(--color-primary-surface)] p-3 rounded-lg group relative"
						>
							<p className="text-sm text-gray-300 whitespace-pre-wrap">
								{entry.content}
							</p>
							<button
								onClick={() =>
									handleDeleteEntry(entry.block_id)
								}
								className="absolute top-2 right-2 p-1 text-gray-500 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
							>
								<IconTrash size={14} />
							</button>
						</div>
					))
				) : (
					<p className="text-center text-gray-500 mt-10">
						No entries for this day.
					</p>
				)}
			</div>

			<div className="mt-6 pt-4 border-t border-[var(--color-primary-surface)]">
				<h3 className="text-lg font-semibold mb-2">Add New Entry</h3>
				<textarea
					value={newEntryContent}
					onChange={(e) => setNewEntryContent(e.target.value)}
					placeholder="What's on your mind?"
					className="w-full p-2 bg-[var(--color-primary-surface)] rounded-md h-24"
					rows={4}
				/>
				<button
					onClick={handleAddEntry}
					disabled={isSubmitting || !newEntryContent.trim()}
					className="w-full mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-500"
				>
					{isSubmitting ? "Adding..." : "Add Entry"}
				</button>
			</div>
		</motion.aside>
	)
}

// CalendarSettingsModal
const CalendarSettingsModal = ({ viewDate, onViewDateChange, onClose }) => {
	const [pickerMonth, setPickerMonth] = useState(startOfMonth(viewDate))

	useEffect(() => {
		// This effect synchronizes the picker's displayed month with the main calendar's
		// viewDate prop. It runs only when viewDate changes. The original implementation
		// included pickerMonth in the dependency array, which caused the picker to
		// reset immediately after navigating to a new month.
		setPickerMonth(startOfMonth(viewDate))
	}, [viewDate])

	const changePickerMonth = (amount) =>
		setPickerMonth((prev) => addMonths(prev, amount))

	const changePickerYear = (amount) => {
		setPickerMonth((prev) => addYears(prev, amount))
	}

	const monthStart = startOfMonth(pickerMonth)
	const monthEnd = endOfMonth(pickerMonth)
	const daysInMonth = eachDayOfInterval({
		start: startOfWeek(monthStart),
		end: endOfWeek(monthEnd)
	})

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={onClose}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-[var(--color-primary-surface)] p-6 rounded-2xl shadow-xl w-full max-w-sm border border-[var(--color-primary-surface-elevated)]"
			>
				<div className="flex justify-between items-center mb-4">
					<button
						onClick={() => changePickerMonth(-1)}
						className="p-2 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
					>
						<IconChevronLeft />
					</button>
					<div className="text-center">
						<h3 className="text-xl font-bold">
							{format(pickerMonth, "MMMM")}
						</h3>
						<div className="flex items-center justify-center gap-1 text-sm text-gray-400">
							<button
								onClick={() => changePickerYear(-1)}
								className="p-0.5 rounded-full hover:bg-gray-700"
							>
								<IconChevronLeft size={14} />
							</button>
							<span>{format(pickerMonth, "yyyy")}</span>
							<button
								onClick={() => changePickerYear(1)}
								className="p-0.5 rounded-full hover:bg-gray-700"
							>
								<IconChevronRight size={14} />
							</button>
						</div>
					</div>
					<button
						onClick={() => changePickerMonth(1)}
						className="p-2 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
					>
						<IconChevronRight />
					</button>
				</div>

				<div className="grid grid-cols-7 gap-y-2 text-center text-sm text-gray-400 mb-3">
					{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(
						(day) => (
							<div key={day}>{day}</div>
						)
					)}
				</div>
				<div className="grid grid-cols-7 gap-1">
					{daysInMonth.map((day) => (
						<button
							key={day.toString()}
							onClick={() => {
								onViewDateChange(day)
								onClose()
							}}
							className={cn(
								"h-10 w-10 flex items-center justify-center rounded-full transition-colors",
								!isSameMonth(day, pickerMonth) &&
									"text-gray-600",
								isToday(day) && "ring-2 ring-blue-500",
								isSameDay(day, viewDate) &&
									"bg-blue-600 text-white",
								"hover:bg-[var(--color-primary-surface-elevated)]"
							)}
						>
							{format(day, "d")}
						</button>
					))}
				</div>
				<div className="flex justify-end gap-3 mt-6 flex-shrink-0">
					<button
						onClick={onClose}
						className="px-4 py-2 text-sm rounded-lg hover:bg-[var(--color-primary-surface-elevated)]"
					>
						Close
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

// Main Journal Page Component
const JournalPage = () => {
	const [viewDate, setViewDate] = useState(new Date())
	const [allTasks, setAllTasks] = useState([])
	const [allJournalEntries, setAllJournalEntries] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [isSidePanelOpen, setSidePanelOpen] = useState(false)
	const [selectedDateForPanel, setSelectedDateForPanel] = useState(null)
	const [isSettingsOpen, setSettingsOpen] = useState(false)
	const router = useRouter()

	const mainContentRef = useRef(null)
	useSmoothScroll(mainContentRef)

	const weekStart = useMemo(
		() => startOfWeek(viewDate, { weekStartsOn: 0 }),
		[viewDate]
	)

	// Auto-scroll to current time on load
	useEffect(() => {
		if (
			!isLoading &&
			isWithinInterval(new Date(), {
				start: weekStart,
				end: endOfWeek(weekStart)
			})
		) {
			const scrollContainer = mainContentRef.current
			if (scrollContainer) {
				const currentHour = new Date().getHours()
				const targetHour = Math.max(0, currentHour - 1) // Scroll to an hour before current time for better visibility
				// Assuming 24 sections of h-24 (6rem)
				const hourHeightInPixels = 6 * 16
				scrollContainer.scrollTo({
					top: targetHour * hourHeightInPixels,
					behavior: "smooth"
				})
			}
		}
	}, [isLoading, weekStart])

	// Fetch journal entries and tasks for the current week
	const fetchData = useCallback(async (start, end) => {
		setIsLoading(true)
		const startDate = format(start, "yyyy-MM-dd")
		const endDate = format(end, "yyyy-MM-dd")

		try {
			// Fetch entries for the week, and ALL tasks for the user
			const [tasksRes, entriesRes] = await Promise.all([
				fetch("/api/tasks"),
				fetch(`/api/journal?startDate=${startDate}&endDate=${endDate}`)
			])

			if (!tasksRes.ok) throw new Error("Failed to fetch tasks")
			if (!entriesRes.ok)
				throw new Error("Failed to fetch journal entries")

			const tasksData = await tasksRes.json()
			const entriesData = await entriesRes.json()

			setAllTasks(tasksData.tasks || [])
			setAllJournalEntries(entriesData.blocks || [])
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		const end = endOfWeek(weekStart, { weekStartsOn: 0 })
		fetchData(weekStart, end)
	}, [weekStart, fetchData])

	const calendarEvents = useMemo(() => {
		const events = []
		const weekEnd = endOfWeek(weekStart, { weekStartsOn: 0 })
		const interval = { start: weekStart, end: weekEnd }

		allTasks.forEach((task) => {
			if (task.enabled === false) return // Skip disabled tasks

			if (task.schedule?.type === "recurring") {
				const [hour, minute] = task.schedule.time
					?.split(":")
					.map(Number) || [9, 0]

				eachDayOfInterval(interval).forEach((day) => {
					let shouldRun = false
					if (task.schedule.frequency === "daily") {
						shouldRun = true
					} else if (
						task.schedule.frequency === "weekly" &&
						task.schedule.days?.includes(format(day, "eeee"))
					) {
						shouldRun = true
					}

					if (shouldRun) {
						events.push({
							...task,
							type: "task",
							startTime: setMinutes(setHours(day, hour), minute),
							endTime: setMinutes(setHours(day, hour + 1), minute) // Assume 1 hr duration
						})
					}
				})
			} else if (task.schedule?.type === "once" && task.schedule.run_at) {
				const runAt = parseISO(task.schedule.run_at)
				if (isWithinInterval(runAt, interval)) {
					events.push({
						...task,
						type: "task",
						startTime: runAt,
						endTime: addHours(runAt, 1) // Assume 1 hr duration
					})
				}
			}
		})
		return events
	}, [allTasks, weekStart])

	const refreshData = () => {
		const end = endOfWeek(weekStart, { weekStartsOn: 0 })
		fetchData(weekStart, end)
	}

	const handleDayClick = (day) => {
		setSelectedDateForPanel(day)
		setSidePanelOpen(true)
	}

	const handleTaskClick = (task) => {
		router.push(`/tasks?taskId=${task.task_id}`)
	}

	return (
		<div className="flex h-screen bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/20 text-[var(--color-text-primary)] overflow-x-hidden pl-0 md:pl-20">
			<div className="flex-1 flex flex-col overflow-hidden h-screen">
				<CalendarHeader
					viewDate={viewDate}
					onViewDateChange={setViewDate}
					onSettingsOpen={() => setSettingsOpen(true)}
				/>
				<main
					ref={mainContentRef}
					className="flex-1 overflow-auto custom-scrollbar"
				>
					{isLoading ? (
						<div className="flex justify-center items-center h-full">
							<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
						</div>
					) : (
						<CalendarGrid
							viewDate={viewDate}
							events={calendarEvents}
							onDayClick={handleDayClick}
							onTaskClick={handleTaskClick}
						/>
					)}
				</main>
			</div>

			<AnimatePresence>
				{isSidePanelOpen && (
					<JournalSidePanel
						selectedDate={selectedDateForPanel}
						entries={allJournalEntries.filter((e) =>
							isSameDay(
								parseISO(e.page_date),
								selectedDateForPanel
							)
						)}
						onClose={() => setSidePanelOpen(false)}
						onDataChange={refreshData}
					/>
				)}
			</AnimatePresence>

			<AnimatePresence>
				{isSettingsOpen && (
					<CalendarSettingsModal
						viewDate={viewDate}
						onViewDateChange={setViewDate}
						onClose={() => setSettingsOpen(false)}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}

export default JournalPage
