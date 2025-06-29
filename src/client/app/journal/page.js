"use client"

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react"
import Sidebar from "@components/Sidebar"
import toast from "react-hot-toast"
import {
	IconMenu2,
	IconChevronLeft,
	IconChevronRight,
	IconLoader,
	IconX,
	IconPencil,
	IconTrash,
	IconPointFilled,
	IconSparkles
} from "@tabler/icons-react"
import { AnimatePresence, motion } from "framer-motion"
import { cn } from "@utils/cn"
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
	subMonths,
	getDay,
	isToday,
	setHours,
	setMinutes
} from "date-fns"

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
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [currentMonth, setCurrentMonth] = useState(new Date())
	const [selectedDate, setSelectedDate] = useState(null)
	const [isPanelOpen, setPanelOpen] = useState(false)
	const [allJournalEntries, setAllJournalEntries] = useState([])
	const [allTasks, setAllTasks] = useState([])
	const [isLoading, setIsLoading] = useState(true)

	// Fetch user details for the sidebar
	useEffect(() => {
		fetch("/api/user/profile")
			.then((res) => res.json())
			.then((data) => setUserDetails(data))
	}, [])

	// Fetch journal entries and tasks for the current month
	const fetchMonthData = useCallback(async (month) => {
		setIsLoading(true)
		const monthStart = startOfMonth(month)
		const monthEnd = endOfMonth(month)
		const startDate = format(monthStart, "yyyy-MM-dd")
		const endDate = format(monthEnd, "yyyy-MM-dd")

		try {
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
		fetchMonthData(currentMonth)
	}, [currentMonth, fetchMonthData])

	const handleDateClick = (day) => {
		setSelectedDate(day)
		setPanelOpen(true)
	}

	const handleClosePanel = () => {
		setPanelOpen(false)
		setSelectedDate(null)
	}

	const changeMonth = (amount) => {
		setCurrentMonth((prev) =>
			amount > 0 ? addMonths(prev, 1) : subMonths(prev, 1)
		)
	}

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

	const calendarEvents = useMemo(() => {
		if (!allTasks.length) return {}

		const eventsByDate = {}
		const monthStart = startOfWeek(startOfMonth(currentMonth))
		const monthEnd = endOfWeek(endOfMonth(currentMonth))
		const interval = { start: monthStart, end: monthEnd }

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
	}, [allTasks, currentMonth])

	const refreshData = () => {
		fetchMonthData(currentMonth)
	}

	return (
		<div className="flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)]">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col overflow-hidden">
				<CalendarHeader
					currentMonth={currentMonth}
					onMonthChange={changeMonth}
					onToday={() => setCurrentMonth(new Date())}
					onToggleSidebar={() => setSidebarVisible(true)}
				/>
				<main className="flex-1 overflow-y-auto p-4 custom-scrollbar">
					{isLoading ? (
						<div className="flex justify-center items-center h-full">
							<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
						</div>
					) : (
						<CalendarGrid
							currentMonth={currentMonth}
							onDateClick={handleDateClick}
							entries={journalEntriesByDate}
							events={calendarEvents}
						/>
					)}
				</main>
			</div>
			<AnimatePresence>
				{isPanelOpen && selectedDate && (
					<EntrySidePanel
						selectedDate={selectedDate}
						onClose={handleClosePanel}
						entries={
							journalEntriesByDate[
								format(selectedDate, "yyyy-MM-dd")
							] || []
						}
						onDataChange={refreshData}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}

// Calendar Header Component
const CalendarHeader = ({
	currentMonth,
	onMonthChange,
	onToday,
	onToggleSidebar
}) => (
	<header className="flex items-center justify-between p-4 border-b border-[var(--color-primary-surface)] shrink-0">
		<div className="flex items-center gap-4">
			<button
				onClick={onToggleSidebar}
				className="text-[var(--color-text-primary)] md:hidden p-2 hover:bg-[var(--color-primary-surface)] rounded-[var(--radius-base)] transition-colors"
			>
				<IconMenu2 />
			</button>
			<h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
				Journal
			</h1>
		</div>
		<div className="flex items-center gap-4">
			<button
				onClick={onToday}
				className="px-4 py-1.5 text-sm font-medium border border-[var(--color-primary-surface-elevated)] rounded-[var(--radius-base)] hover:bg-[var(--color-primary-surface)] transition-colors"
			>
				Today
			</button>
			<div className="flex items-center">
				<button
					onClick={() => onMonthChange(-1)}
					className="p-2 rounded-full hover:bg-[var(--color-primary-surface)]"
				>
					<IconChevronLeft size={20} />
				</button>
				<h2 className="w-40 text-center text-lg font-semibold">
					{format(currentMonth, "MMMM yyyy")}
				</h2>
				<button
					onClick={() => onMonthChange(1)}
					className="p-2 rounded-full hover:bg-[var(--color-primary-surface)]"
				>
					<IconChevronRight size={20} />
				</button>
			</div>
		</div>
	</header>
)

// Calendar Grid Component
const CalendarGrid = ({ currentMonth, onDateClick, entries, events }) => {
	const monthStart = startOfMonth(currentMonth)
	const monthEnd = endOfMonth(currentMonth)
	const startDate = startOfWeek(monthStart)
	const endDate = endOfWeek(monthEnd)
	const days = eachDayOfInterval({ start: startDate, end: endDate })

	return (
		<div className="grid grid-cols-7 flex-1">
			{weekDays.map((day) => (
				<div
					key={day}
					className="text-center font-medium text-xs text-[var(--color-text-muted)] py-2 border-b border-[var(--color-primary-surface)]"
				>
					{day}
				</div>
			))}
			{days.map((day) => (
				<DayCell
					key={day.toString()}
					day={day}
					currentMonth={currentMonth}
					onDateClick={onDateClick}
					entriesForDay={entries[format(day, "yyyy-MM-dd")] || []}
					eventsForDay={events[format(day, "yyyy-MM-dd")] || []}
				/>
			))}
		</div>
	)
}

// Day Cell Component
const DayCell = ({
	day,
	currentMonth,
	onDateClick,
	entriesForDay,
	eventsForDay
}) => {
	const isCurrentMonth = isSameMonth(day, currentMonth)
	const isCurrentDay = isToday(day)

	return (
		<div
			className={cn(
				"relative flex flex-col min-h-[120px] border border-[var(--color-primary-surface)] p-2 transition-colors duration-200",
				isCurrentMonth
					? "bg-[var(--color-primary-background)] hover:bg-[var(--color-primary-surface)]/50"
					: "bg-[var(--color-primary-surface)]/30 text-[var(--color-text-muted)] hover:bg-[var(--color-primary-surface)]/50",
				"cursor-pointer"
			)}
			onClick={() => onDateClick(day)}
		>
			<div
				className={cn(
					"w-7 h-7 flex items-center justify-center text-sm rounded-full",
					isCurrentDay &&
						"bg-[var(--color-accent-blue)] text-white font-bold"
				)}
			>
				{format(day, "d")}
			</div>
			{entriesForDay.length > 0 && (
				<IconPointFilled className="absolute top-2 right-2 text-purple-400 w-4 h-4" />
			)}
			<div className="mt-1 space-y-1 overflow-hidden">
				{eventsForDay.slice(0, 3).map((event) => (
					<div
						key={event.task_id}
						className={cn(
							"text-xs text-white rounded px-2 py-0.5 truncate border-l-2",
							taskStatusColors[event.status] ||
								taskStatusColors.default
						)}
						title={event.description}
					>
						<span className="font-bold">
							{format(event.startTime, "ha")}
						</span>{" "}
						{event.description}
					</div>
				))}
				{eventsForDay.length > 3 && (
					<div className="text-xs text-[var(--color-text-muted)]">
						+ {eventsForDay.length - 3} more
					</div>
				)}
			</div>
		</div>
	)
}

// Side Panel for Entries
const EntrySidePanel = ({ selectedDate, onClose, entries, onDataChange }) => {
	const [newContent, setNewContent] = useState("")
	const [editingBlock, setEditingBlock] = useState(null)
	const [isSubmitting, setIsSubmitting] = useState(false)
	const newEntryTextareaRef = useRef(null)

	const handleCreateBlock = async () => {
		if (!newContent.trim()) return
		setIsSubmitting(true)

		const newOrder =
			entries.length > 0
				? Math.max(...entries.map((b) => b.order)) + 1
				: 0
		try {
			const response = await fetch("/api/journal", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					content: newContent,
					page_date: format(selectedDate, "yyyy-MM-dd"),
					order: newOrder,
					processWithAI: true // Always process with AI now
				})
			})
			if (!response.ok) throw new Error("Failed to create entry")
			setNewContent("")
			toast.success("Entry saved and sent for processing.")
			onDataChange()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	const handleUpdateBlock = async (blockId, content) => {
		setIsSubmitting(true)
		try {
			const response = await fetch(`/api/journal?blockId=${blockId}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ content })
			})
			if (!response.ok) throw new Error("Failed to update block")
			setEditingBlock(null)
			toast.success("Entry updated.")
			onDataChange()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	const handleDeleteBlock = async (blockId) => {
		if (!window.confirm("Are you sure you want to delete this entry?"))
			return

		setIsSubmitting(true)
		try {
			const response = await fetch(`/api/journal?blockId=${blockId}`, {
				method: "DELETE"
			})
			if (!response.ok) throw new Error("Failed to delete block")
			toast.success("Entry deleted.")
			onDataChange()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	return (
		<motion.div
			initial={{ x: "100%" }}
			animate={{ x: 0 }}
			exit={{ x: "100%" }}
			transition={{ type: "spring", stiffness: 300, damping: 30 }}
			className="fixed top-0 right-0 h-full w-full max-w-md bg-[var(--color-primary-surface)] shadow-lg z-50 flex flex-col border-l border-[var(--color-primary-surface-elevated)]"
		>
			<header className="flex items-center justify-between p-4 border-b border-[var(--color-primary-surface-elevated)]">
				<h2 className="text-lg font-semibold">
					{format(selectedDate, "eeee, MMMM d, yyyy")}
				</h2>
				<button
					onClick={onClose}
					className="p-1 rounded-full hover:bg-[var(--color-primary-surface-elevated)]"
				>
					<IconX size={20} />
				</button>
			</header>

			<div className="flex-1 p-4 space-y-4 overflow-y-auto custom-scrollbar">
				{entries.length === 0 ? (
					<p className="text-center text-[var(--color-text-muted)] pt-10">
						No entries for this day.
					</p>
				) : (
					entries.map((block) => (
						<div
							key={block.block_id}
							className="group relative bg-[var(--color-primary-background)] p-3 rounded-lg border border-transparent hover:border-[var(--color-primary-surface-elevated)]"
						>
							{editingBlock?.block_id === block.block_id ? (
								<div>
									<textarea
										value={editingBlock.content}
										onChange={(e) =>
											setEditingBlock({
												...editingBlock,
												content: e.target.value
											})
										}
										className="w-full bg-transparent resize-none focus:outline-none p-1"
									/>
									<div className="flex justify-end gap-2 mt-2">
										<button
											onClick={() =>
												setEditingBlock(null)
											}
											className="text-xs px-2 py-1 rounded"
										>
											Cancel
										</button>
										<button
											onClick={() =>
												handleUpdateBlock(
													editingBlock.block_id,
													editingBlock.content
												)
											}
											className="text-xs px-2 py-1 bg-[var(--color-accent-blue)] rounded text-white"
										>
											Save
										</button>
									</div>
								</div>
							) : (
								<>
									<p className="whitespace-pre-wrap">
										{block.content}
									</p>
									<div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
										<button
											onClick={() =>
												setEditingBlock(block)
											}
											className="p-1 rounded text-[var(--color-text-muted)] hover:text-white"
										>
											<IconPencil size={14} />
										</button>
										<button
											onClick={() =>
												handleDeleteBlock(
													block.block_id
												)
											}
											className="p-1 rounded text-[var(--color-text-muted)] hover:text-red-400"
										>
											<IconTrash size={14} />
										</button>
									</div>
								</>
							)}
						</div>
					))
				)}
			</div>

			<div className="p-4 border-t border-[var(--color-primary-surface-elevated)] space-y-2">
				<textarea
					ref={newEntryTextareaRef}
					value={newContent}
					onChange={(e) => setNewContent(e.target.value)}
					placeholder="Write something..."
					className="w-full bg-[var(--color-primary-background)] p-2 rounded-lg resize-none focus:outline-none placeholder:text-[var(--color-text-muted)]"
					rows={4}
				/>
				<div className="flex justify-end">
					<button
						onClick={handleCreateBlock}
						disabled={isSubmitting || !newContent.trim()}
						className="px-4 py-1.5 text-sm font-medium bg-[var(--color-accent-blue)] hover:bg-blue-500 text-white rounded-md disabled:opacity-50"
					>
						Save
					</button>
				</div>
			</div>
		</motion.div>
	)
}

export default JournalPage
