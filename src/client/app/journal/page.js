"use client"

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react"
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
	IconPointFilled,
	IconSparkles
} from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"
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
	subMonths,
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
	pending: "bg-yellow-500/80 border-yellow-400",
	processing: "bg-blue-500/80 border-blue-400",
	completed: "bg-green-500/80 border-green-400",
	error: "bg-red-500/80 border-red-400",
	approval_pending: "bg-purple-500/80 border-purple-400",
	active: "bg-green-500/80 border-green-400",
	cancelled: "bg-gray-600/80 border-gray-500",
	default: "bg-gray-500/80 border-gray-400"
}

// Main Journal Page Component
const JournalPage = () => {
	const [viewDate, setViewDate] = useState(new Date())
	const [selectedDayForNewEntry, setSelectedDayForNewEntry] = useState(null)
	const [activeBlock, setActiveBlock] = useState({
		block: null,
		isEditing: false
	})
	const [deletingBlock, setDeletingBlock] = useState(null)
	const [isCalendarOpen, setCalendarOpen] = useState(false)
	const [allJournalEntries, setAllJournalEntries] = useState([])
	const [allTasks, setAllTasks] = useState([])
	const [isLoading, setIsLoading] = useState(true)

	const mainContentRef = useRef(null)
	useSmoothScroll(mainContentRef)

	// FIX: Memoize currentWeekStart to prevent re-creating the Date object on every render, which caused the infinite loop.
	const currentWeekStart = useMemo(
		() => startOfWeek(viewDate, { weekStartsOn: 0 }),
		[viewDate]
	)

	// Fetch journal entries and tasks for the current week
	const fetchWeekData = useCallback(async (weekStart) => {
		setIsLoading(true)
		const weekEnd = endOfWeek(weekStart, { weekStartsOn: 0 })
		const startDate = format(weekStart, "yyyy-MM-dd")
		const endDate = format(weekEnd, "yyyy-MM-dd")

		try {
			// Fetch entries for the week, and ALL tasks for the user
			const [entriesRes, tasksRes] = await Promise.all([
				fetch(`/api/journal?startDate=${startDate}&endDate=${endDate}`),
				fetch("/api/tasks")
			])

			if (!entriesRes.ok)
				throw new Error("Failed to fetch journal entries")
			if (!tasksRes.ok) throw new Error("Failed to fetch tasks")

			const entriesData = await entriesRes.json()
			const tasksData = await tasksRes.json()

			setAllJournalEntries(entriesData.blocks || [])
			setAllTasks(tasksData.tasks || [])
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchWeekData(currentWeekStart)
	}, [currentWeekStart, fetchWeekData])

	const changeWeek = (amount) => {
		setViewDate((prev) => addDays(prev, amount * 7))
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
		const weekStart = startOfWeek(viewDate, { weekStartsOn: 0 })
		const weekEnd = endOfWeek(viewDate, { weekStartsOn: 0 })
		const interval = { start: weekStart, end: weekEnd }

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
		fetchWeekData(currentWeekStart)
	}

	return (
		<div className="flex h-screen bg-gradient-to-br from-[var(--color-primary-background)] via-[var(--color-primary-background)] to-[var(--color-primary-surface)]/20 text-[var(--color-text-primary)] overflow-x-hidden pl-0 md:pl-20">
			<Tooltip id="journal-tooltip" />
			<div className="flex-1 flex flex-col overflow-hidden h-screen">
				<CalendarHeader
					viewDate={viewDate}
					onWeekChange={changeWeek}
					onDayChange={changeDay}
					onToday={() => setViewDate(new Date())}
					onCalendarOpen={() => setCalendarOpen(true)}
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
							viewDate={viewDate}
							entriesByDate={journalEntriesByDate}
							recurringTasksByDate={recurringTasksByDate}
							tasksById={tasksById}
							onAddEntry={(day) => setSelectedDayForNewEntry(day)}
							onViewEntry={(block) =>
								setActiveBlock({ block, isEditing: false })
							}
							onEditEntry={(block) =>
								setActiveBlock({ block, isEditing: true })
							}
							onDeleteEntry={(block) => setDeletingBlock(block)}
						/>
					)}
				</main>
			</div>
			<aside className="w-[320px] shrink-0 border-l border-[var(--color-primary-surface)]/50 bg-[var(--color-primary-background)]/80 backdrop-blur-lg p-6 hidden lg:flex flex-col">
				<RightSideCalendar
					viewDate={viewDate}
					onDateChange={setViewDate}
					entriesByDate={journalEntriesByDate}
					recurringTasksByDate={recurringTasksByDate}
				/>
			</aside>
			<AnimatePresence>
				{isCalendarOpen && (
					<motion.div
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						onClick={() => setCalendarOpen(false)}
						className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 p-4 lg:hidden flex justify-center items-center"
					>
						<motion.div
							initial={{ scale: 0.9, y: 20 }}
							animate={{ scale: 1, y: 0 }}
							exit={{ scale: 0.9, y: 20 }}
							onClick={(e) => e.stopPropagation()}
							className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-sm border border-[var(--color-primary-surface-elevated)]"
						>
							<RightSideCalendar
								viewDate={viewDate}
								onDateChange={(date) => {
									setViewDate(date)
									setCalendarOpen(false)
								}}
								entriesByDate={journalEntriesByDate}
								recurringTasksByDate={recurringTasksByDate}
							/>
						</motion.div>
					</motion.div>
				)}
			</AnimatePresence>
			<AnimatePresence>
				{selectedDayForNewEntry && (
					<AddEntryModal
						day={selectedDayForNewEntry}
						onClose={() => setSelectedDayForNewEntry(null)}
						onDataChange={refreshData}
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

// Calendar Header Component
const CalendarHeader = ({
	viewDate,
	onWeekChange,
	onDayChange,
	onToday,
	onCalendarOpen
}) => {
	const weekStart = startOfWeek(viewDate, { weekStartsOn: 0 })
	const weekEnd = endOfWeek(weekStart, { weekStartsOn: 0 })
	return (
		<motion.header
			initial={{ y: -20, opacity: 0 }}
			animate={{ y: 0, opacity: 1 }}
			transition={{ duration: 0.6, ease: "easeOut" }}
			className="flex items-center justify-between p-4 md:p-6 border-b border-[var(--color-primary-surface)]/50 backdrop-blur-md bg-[var(--color-primary-background)]/90 shrink-0"
		>
			<motion.div
				className="flex items-center gap-4"
				whileHover={{ scale: 1.02 }}
				transition={{ type: "spring", stiffness: 400, damping: 17 }}
			>
				<h1 className="text-2xl font-bold font-Inter text-lightblue">
					Journal
				</h1>
			</motion.div>
			<div className="flex items-center gap-2 md:gap-6">
				<motion.button
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
						key={format(weekStart, "yyyy-MM-dd")}
						initial={{ opacity: 0, y: 10 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ duration: 0.3 }}
						className="w-56 text-center text-lg font-semibold px-4"
					>
						{format(weekStart, "MMMM d")} -{" "}
						{format(weekEnd, "d, yyyy")}
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
					<button
						onClick={onCalendarOpen}
						className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95 md:hidden"
					>
						<IconCalendar size={18} />
					</button>
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
	onAddEntry,
	onViewEntry,
	onEditEntry,
	onDeleteEntry,
	tasksById
}) => {
	const weekStart = startOfWeek(viewDate, { weekStartsOn: 0 })
	const days = eachDayOfInterval({
		start: weekStart,
		end: endOfWeek(weekStart, { weekStartsOn: 0 })
	})

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			transition={{ duration: 0.5, delay: 0.1 }}
			className="grid grid-cols-1 md:grid-cols-7 gap-4 flex-1 h-full"
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
						onAddEntry={onAddEntry}
						onViewEntry={onViewEntry}
						onEditEntry={onEditEntry}
						onDeleteEntry={onDeleteEntry}
					/>
				</div>
			))}
		</motion.div>
	)
}

// Day Column Component
const DayColumn = ({
	day,
	journalEntries,
	recurringTasks,
	onAddEntry,
	onViewEntry,
	onEditEntry,
	onDeleteEntry,
	tasksById
}) => {
	const isCurrentDay = isToday(day)

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
						{format(day, "eee")}
					</span>
					<span
						className={cn(
							"text-2xl font-bold",
							isCurrentDay
								? "text-white"
								: "text-[var(--color-text-muted)]"
						)}
					>
						{format(day, "d")}
					</span>
				</h3>
				<button
					onClick={() => onAddEntry(day)}
					className="p-1.5 rounded-lg hover:bg-[var(--color-primary-surface)] transition-colors"
					data-tooltip-id="journal-tooltip"
					data-tooltip-content="Add new entry"
				>
					<IconPlus size={16} />
				</button>
			</div>
			<div className="p-3 space-y-3 flex-1 overflow-y-auto custom-scrollbar">
				{recurringTasks.map((task, index) => (
					<EntryCard
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
					<EntryCard
						key={`journal-${entry.block_id}`}
						item={{ ...entry, type: "journal" }}
						linkedTask={tasksById[entry.linked_task_id]}
						onViewEntry={onViewEntry}
						onEditEntry={onEditEntry}
						onDeleteEntry={onDeleteEntry}
					/>
				))}
				{recurringTasks.length === 0 && journalEntries.length === 0 && (
					<div className="text-center py-10 text-sm text-[var(--color-text-muted)]">
						No entries.
					</div>
				)}
			</div>
		</motion.div>
	)
}

// Entry Card Component
const EntryCard = ({
	item,
	linkedTask,
	onViewEntry,
	onEditEntry,
	onDeleteEntry
}) => {
	const isJournal = item.type === "journal"
	const taskStatus = linkedTask?.status
	const statusInfo = taskStatusColors[taskStatus] || taskStatusColors.default

	return (
		<motion.div
			initial={{ opacity: 0, x: -10 }}
			animate={{ opacity: 1, x: 0 }}
			whileHover={{
				y: -3,
				scale: 1.02,
				rotateX: 1,
				rotateY: -1,
				boxShadow:
					"0 10px 15px -3px rgba(0, 178, 254, 0.1), 0 4px 6px -2px rgba(0, 178, 254, 0.05)"
			}}
			onClick={() => onViewEntry(item)}
			className={cn(
				"bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-3 rounded-lg border cursor-pointer backdrop-blur-sm shadow-sm group",
				isJournal ? "border-transparent" : `border-l-4 ${statusInfo}`
			)}
			style={{ transformStyle: "preserve-3d" }}
		>
			<div className="flex-grow">
				{isJournal ? (
					<p className="text-sm leading-relaxed whitespace-pre-wrap">
						{item.content}
					</p>
				) : (
					<div className="flex items-center gap-2">
						<span
							className={`w-2.5 h-2.5 rounded-full ${statusInfo}`}
						></span>
						<p className="text-sm font-medium">{item.content}</p>
					</div>
				)}
			</div>
			{(taskStatus || isJournal) && (
				<div className="flex items-end justify-between mt-2 pt-2 border-t border-white/5 min-h-[28px]">
					<div>
						{taskStatus && (
							<div className="text-xs font-semibold text-gray-400 capitalize flex items-center gap-1.5">
								<IconSparkles size={12} />
								<span>
									Task: {taskStatus.replace("_", " ")}
								</span>
							</div>
						)}
					</div>
					{isJournal && (
						<div className="relative flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
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
								className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-all"
								data-tooltip-id="journal-tooltip"
								data-tooltip-content="Delete"
							>
								<IconTrash size={14} />
							</motion.button>
						</div>
					)}
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
								<span className="absolute bottom-1.5 h-1 w-1 bg-purple-400 rounded-full"></span>
							)}
						</button>
					)
				})}
			</div>
			<div className="mt-auto pt-6 text-sm text-gray-500">
				<p className="font-semibold text-gray-400 mb-2">Legend:</p>
				<div className="flex items-center gap-2 mb-1">
					<span className="h-2 w-2 rounded-full bg-purple-400"></span>{" "}
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

// Add Entry Modal Component
const AddEntryModal = ({ day, onClose, onDataChange }) => {
	const [content, setContent] = useState("")
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleCreate = async () => {
		if (!content.trim()) return
		setIsSubmitting(true)
		try {
			const response = await fetch("/api/journal", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					content: content,
					page_date: format(day, "yyyy-MM-dd"),
					order: 0, // Simplified order for now
					processWithAI: true
				})
			})
			if (!response.ok) throw new Error("Failed to create entry")
			toast.success("Entry saved and sent for processing.")
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
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-lg border border-[var(--color-primary-surface-elevated)]"
			>
				<div className="flex justify-between items-center mb-4">
					<h2 className="text-xl font-bold">
						Add Entry for {format(day, "MMMM d")}
					</h2>
					<button
						onClick={onClose}
						className="p-1 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
					>
						<IconX size={18} />
					</button>
				</div>
				<textarea
					value={content}
					onChange={(e) => setContent(e.target.value)}
					placeholder="Write something..."
					className="w-full bg-gradient-to-br from-[var(--color-primary-background)] to-[var(--color-primary-surface)]/30 p-4 rounded-xl resize-none focus:outline-none placeholder:text-[var(--color-text-muted)] border border-transparent focus:border-[var(--color-accent-blue)]/30 transition-all duration-300 backdrop-blur-sm"
					rows={6}
				/>
				<div className="flex justify-end gap-3 mt-4">
					<button
						onClick={onClose}
						className="px-4 py-2 text-sm rounded-lg hover:bg-[var(--color-primary-surface-elevated)]"
					>
						Cancel
					</button>
					<button
						onClick={handleCreate}
						disabled={isSubmitting || !content.trim()}
						className="px-6 py-2 text-sm font-medium bg-gradient-to-r from-[var(--color-accent-blue)] to-blue-600 text-white rounded-xl disabled:opacity-50 shadow-lg shadow-[var(--color-accent-blue)]/20"
					>
						{isSubmitting ? "Saving..." : "Save"}
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
						className="px-6 py-2 text-sm font-medium bg-red-600 hover:bg-red-500 text-white rounded-xl disabled:opacity-50 shadow-lg shadow-red-500/20"
					>
						{isSubmitting ? "Deleting..." : "Delete"}
					</button>
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
					<h2 className="text-xl font-bold text-lightblue">
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
									className="text-xs p-1.5 rounded-md hover:bg-red-500/20 hover:text-red-400"
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
								<IconSparkles size={18} /> Linked Task
								<button
									className="text-xs text-blue-400 hover:underline"
									onClick={() => router.push("/tasks")}
								>
									View in Tasks
								</button>
							</h3>
							<div className="space-y-4">
								<div>
									<strong className="text-gray-400">
										Description:
									</strong>{" "}
									{linkedTask.description}
								</div>
								<div>
									<strong className="text-gray-400">
										Status:
									</strong>{" "}
									<span className="capitalize font-semibold">
										{linkedTask.status.replace("_", " ")}
									</span>
								</div>

								<div>
									<strong className="text-gray-400">
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
										<strong className="text-gray-400">
											Progress:
										</strong>
										<ul className="mt-1 space-y-2 text-sm text-[var(--color-text-secondary)]">
											{block.task_progress.map(
												(update, i) => (
													<li
														key={i}
														className="flex gap-2"
													>
														<span className="text-gray-500">
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
										<strong className="text-gray-400">
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
							className="px-6 py-2 text-sm font-medium bg-gradient-to-r from-green-500 to-green-600 text-white rounded-xl disabled:opacity-50 shadow-lg shadow-green-500/20"
						>
							{isSubmitting ? "Approving..." : "Approve Plan"}
						</button>
					)}
				</div>
			</motion.div>
		</motion.div>
	)
}

export default JournalPage
