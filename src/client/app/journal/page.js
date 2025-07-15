"use client"

import React, { useState, useEffect, useCallback, useMemo, useRef } from "react"
import toast from "react-hot-toast"
import { usePostHog } from "posthog-js/react"
import { IconLoader } from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"
import { AnimatePresence } from "framer-motion"
import {
	format,
	eachDayOfInterval,
	addDays,
	subDays,
	getDay,
	setHours,
	setMinutes
} from "date-fns"
import { useSmoothScroll } from "@hooks/useSmoothScroll"
import CalendarHeader from "@components/journal/CalendarHeader"
import WeeklyKanban from "@components/journal/WeeklyKanban"
import SearchOverlay from "@components/journal/SearchOverlay"
import RightSidebar from "@components/journal/RightSidebar"
import EditTaskModal from "@components/journal/EditTaskModal"
import EntryDetailsModal from "@components/journal/EntryDetailsModal"
import TaskDetailsModal from "@components/journal/TaskDetailsModal"
import DeleteConfirmationModal from "@components/journal/DeleteConfirmationModal"

// Main Journal Page Component
const OrganizerPage = () => {
	const [viewDate, setViewDate] = useState(new Date())
	const [searchQuery, setSearchQuery] = useState("")
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
	const posthog = usePostHog()
	const [allJournalEntries, setAllJournalEntries] = useState([])
	const [allTasks, setAllTasks] = useState([]) // Combined loading state
	const [isLoading, setIsLoading] = useState(true) // Combined loading state

	const [integrations, setIntegrations] = useState([]) // For checking connected tools
	const [allTools, setAllTools] = useState([])
	const mainContentRef = useRef(null)
	useSmoothScroll(mainContentRef)

	// MODIFIED: Fetch data for a 3-day view centered on viewDate
	const currentViewStart = useMemo(() => subDays(viewDate, 1), [viewDate]) // eslint-disable-line

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
		fetchDataForView(viewDate) // Fetch data when the view date changes
	}, [viewDate, fetchDataForView])

	const changeDay = useCallback(
		(amount) => setViewDate((prev) => addDays(prev, amount)),
		[]
	)

	const handleShortcuts = useCallback(
		(e) => {
			if (e.ctrlKey) {
				if (e.key === "ArrowLeft") changeDay(-1)
				else if (e.key === "ArrowRight") changeDay(1)
				else if (e.key === "Enter")
					setAddingToDay(format(viewDate, "yyyy-MM-dd"))
				else return
				e.preventDefault()
			}
		},
		[viewDate, changeDay]
	)

	useEffect(() => {
		window.addEventListener("keydown", handleShortcuts)
		return () => window.removeEventListener("keydown", handleShortcuts)
	}, [handleShortcuts])

	const changeWeek = (amount) => {
		setViewDate((prev) => addDays(prev, amount * 3))
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

	const tasksById = useMemo(() => {
		return allTasks.reduce((acc, task) => {
			acc[task.task_id] = task
			return acc
		}, {})
	}, [allTasks])

	const searchResults = useMemo(() => {
		if (!searchQuery) return []
		const lowerQuery = searchQuery.toLowerCase()

		const journalResults = allJournalEntries
			.filter((e) => e.content.toLowerCase().includes(lowerQuery))
			.map((e) => ({ ...e, item_type: "journal" }))

		const taskResults = allTasks
			.filter((t) => t.description.toLowerCase().includes(lowerQuery))
			.map((t) => ({ ...t, item_type: "task" }))

		return [...journalResults, ...taskResults].sort((a, b) => {
			const dateA = a.created_at ? new Date(a.created_at) : 0
			const dateB = b.created_at ? new Date(b.created_at) : 0
			if (dateA && dateB) {
				return dateB - dateA
			}
			return 0
		})
	}, [searchQuery, allJournalEntries, allTasks])

	const isSearching = useMemo(() => {
		return searchQuery.length > 0
	}, [searchQuery])

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
			posthog.capture("task_approved", { task_id: taskId })
			toast.success("Plan approved! Task has been queued for execution.")
			refreshData()
		} catch (error) {
			toast.error(`Error approving task: ${error.message}`)
		}
	}

	const handleAnswerClarifications = async (taskId, answers) => {
		if (!taskId || !answers || answers.length === 0) return
		try {
			const response = await fetch("/api/tasks/clarify", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId, answers })
			})
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(errorData.error || "Failed to submit answers")
			}
			toast.success("Answers submitted! Task will now proceed.")
			refreshData()
		} catch (error) {
			toast.error(`Error submitting answers: ${error.message}`)
		}
	}

	const handleToggleEnableTask = async (taskId, isEnabled) => {
		try {
			const response = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId, enabled: !isEnabled })
			})
			if (!response.ok) {
				const errorData = await response.json()
				throw new Error(
					errorData.error || "Failed to update workflow status."
				)
			}
			toast.success(`Workflow ${!isEnabled ? "resumed" : "paused"}.`)
			refreshData()
		} catch (error) {
			toast.error(error.message)
		}
	}
	const handleDeleteTask = async (taskId) => {
		if (
			!taskId ||
			!window.confirm("Are you sure you want to delete this task?")
		)
			return

		const taskToDelete = allTasks.find((t) => t.task_id === taskId)

		try {
			const response = await fetch("/api/tasks/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId })
			})
			if (!response.ok) throw new Error((await response.json()).error)
			if (taskToDelete?.status === "approval_pending") {
				posthog.capture("task_disapproved", { task_id: taskId })
			}
			toast.success("Task deleted successfully!")
			refreshData()
			setViewingTask(null) // Clear the viewing state to prevent stale UI
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
			posthog.capture("task_edited", {
				task_id: editingTask.task_id,
				is_recurring: editingTask.schedule?.type === "recurring"
			})
			toast.success("Task updated successfully!")
			setEditingTask(null)
			refreshData()
		} catch (error) {
			toast.error(`Failed to update task: ${error.message}`)
		}
	}

	const handleUpdateTaskSchedule = async (taskId, schedule) => {
		if (!taskId) return false
		try {
			const response = await fetch("/api/tasks/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ taskId, schedule })
			})
			if (!response.ok) throw new Error((await response.json()).error)
			toast.success("Task schedule updated!")
			fetchDataForView(viewDate) // Refresh data
			return true // Indicate success
		} catch (error) {
			toast.error(`Failed to update schedule: ${error.message}`)
			return false
		}
	}

	const handleDuplicateEntry = async (originalBlock) => {
		if (!originalBlock.linked_task_id) {
			toast.error("This journal entry is not linked to a task.")
			return
		}
		if (
			!window.confirm("Create a new copy of this task and journal entry?")
		)
			return

		try {
			// 1. Rerun the task to get a new task
			const rerunResponse = await fetch("/api/tasks/rerun", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					taskId: originalBlock.linked_task_id
				})
			})
			if (!rerunResponse.ok)
				throw new Error((await rerunResponse.json()).error)
			const rerunData = await rerunResponse.json()
			const newTaskId = rerunData.new_task_id

			// 2. Create a new journal entry linked to the new task
			const newJournalEntry = {
				content: originalBlock.content,
				page_date: format(new Date(), "yyyy-MM-dd"), // Create it for today
				order: 999, // at the end
				processWithAI: false, // The task is already created
				linked_task_id: newTaskId,
				task_status: "approval_pending" // The new task is pending approval
			}

			const createJournalResponse = await fetch("/api/journal", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(newJournalEntry)
			})
			if (!createJournalResponse.ok)
				throw new Error("Failed to create new journal entry.")

			toast.success("Task and journal entry duplicated successfully!")
			refreshData()
		} catch (error) {
			toast.error(`Failed to duplicate: ${error.message}`)
		}
	}

	const allItemsByDate = useMemo(() => {
		const items = { ...journalEntriesByDate }

		// This is where we project recurring tasks as journal-like entries
		Object.keys(recurringTasksByDate).forEach((date) => {
			if (!items[date]) {
				items[date] = []
			}
			const recurringForDay = recurringTasksByDate[date].map((task) => ({
				block_id: `recurring-${task.task_id}-${date}`, // create a unique key
				content: task.description,
				isRecurring: true,
				linked_task_id: task.task_id,
				page_date: date,
				order: -1 // To show them at the top
			}))
			items[date] = [...recurringForDay, ...items[date]]
		})

		// Sort all items within each day
		Object.keys(items).forEach((date) => {
			items[date].sort((a, b) => a.order - b.order)
		})

		return items
	}, [journalEntriesByDate, recurringTasksByDate])

	return (
		<div className="flex h-screen bg-gradient-to-br from-[var(--color-primary-background)] via-[var(--color-primary-background)] to-[var(--color-primary-surface)]/20 text-[var(--color-text-primary)] overflow-x-hidden pl-0 md:pl-20">
			<Tooltip id="journal-tooltip" />
			<Tooltip id="journal-help" style={{ zIndex: 9999 }} />
			<div className="flex-1 flex flex-col overflow-hidden h-screen relative">
				<CalendarHeader
					viewDate={viewDate}
					onWeekChange={changeWeek} // This will now change by 3 days
					onDayChange={changeDay}
					onToday={() => setViewDate(new Date())}
					searchQuery={searchQuery}
					setSearchQuery={setSearchQuery}
				/>
				<main
					ref={mainContentRef}
					className="flex-1 overflow-y-auto p-4 md:p-6 custom-scrollbar relative"
				>
					{isLoading ? (
						<div className="flex justify-center items-center h-full">
							<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
						</div>
					) : (
						<WeeklyKanban
							viewDate={viewDate} // This will be used by DayColumn for visibility on mobile
							itemsByDate={allItemsByDate}
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
							onDuplicateEntry={handleDuplicateEntry}
							onDataChange={refreshData}
						/>
					)}
					{isSearching && (
						<SearchOverlay
							query={searchQuery}
							results={searchResults}
							onClose={() => setSearchQuery("")}
							onResultClick={(item) => {
								if (item.item_type === "journal") {
									setActiveBlock({
										block: item,
										isEditing: false
									})
								} else {
									setViewingTask(item)
								}
								setSearchQuery("") // Close search on selection
							}}
							tasksById={tasksById}
							onEditEntry={(block) =>
								setActiveBlock({ block, isEditing: true })
							}
							onDeleteEntry={(block) => setDeletingBlock(block)}
							onDuplicateEntry={handleDuplicateEntry}
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
				onToggleEnableTask={handleToggleEnableTask}
				onUpdateSchedule={handleUpdateTaskSchedule}
				onAnswerClarifications={handleAnswerClarifications}
			/>
			<AnimatePresence>
				{editingTask && !viewingTask && !activeBlock.block && (
					<EditTaskModal
						key={editingTask.task_id}
						task={editingTask}
						onClose={() => setEditingTask(null)}
						onSave={handleUpdateTask}
						setTask={setEditingTask}
						onUpdateSchedule={handleUpdateTaskSchedule}
						allTools={allTools}
						integrations={integrations}
					/>
				)}
				{activeBlock.block && ( // This is the new logic to handle journal entry clicks
					<EntryDetailsModal
						key={activeBlock.block.block_id}
						block={activeBlock.block}
						task={
							activeBlock.block.linked_task_id
								? tasksById[activeBlock.block.linked_task_id]
								: null
						}
						startInEditMode={activeBlock.isEditing}
						onClose={() =>
							setActiveBlock({ block: null, isEditing: false })
						}
						onDataChange={refreshData}
						onDeleteRequest={(block) => setDeletingBlock(block)}
					/>
				)}
				{viewingTask &&
					!activeBlock.block && ( // Logic for search result clicks
						<TaskDetailsModal
							task={viewingTask}
							onClose={() => setViewingTask(null)}
							onDataChange={refreshData}
						/>
					)}
				{deletingBlock && !viewingTask && !activeBlock.block && (
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

export default OrganizerPage
