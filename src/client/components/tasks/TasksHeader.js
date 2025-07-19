"use client"

import React from "react"
import { format, subDays, addDays, startOfToday } from "date-fns"
import {
	IconChevronLeft,
	IconChevronRight,
	IconList,
	IconCalendar,
	IconPlus,
	IconLayoutGrid, // This is This Month
	IconCalendarWeek // This is This Week
} from "@tabler/icons-react"
import { cn } from "@utils/cn"

const TasksHeader = ({
	currentDate,
	setCurrentDate,
	viewType,
	setViewType,
	onAddTask,
	onCalendarClick
}) => {
	const onDayChange = (amount) => setCurrentDate(addDays(currentDate, amount))
	const onToday = () => setCurrentDate(startOfToday())

	const viewOptions = [
		{ id: "all", icon: IconList, label: "All Tasks" },
		{ id: "week", icon: IconCalendarWeek, label: "This Week" },
		{ id: "month", icon: IconLayoutGrid, label: "This Month" }
	]

	return (
		<header className="flex items-center justify-between p-4 md:px-8 md:py-6 border-b border-[var(--color-primary-surface)] flex-shrink-0">
			<div className="flex items-center gap-6">
				<h1 className="text-3xl lg:text-4xl font-semibold text-[var(--color-text-primary)]">
					Tasks
				</h1>
				{/* View Toggles */}
				<div className="flex items-center gap-1 bg-dark-surface p-1 rounded-lg">
					{viewOptions.map((opt) => (
						<button
							key={opt.id}
							onClick={() => setViewType(opt.id)}
							className={cn(
								"px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
								viewType === opt.id
									? "bg-sentient-blue text-white"
									: "text-neutral-400 hover:bg-dark-surface-elevated hover:text-white"
							)}
						>
							{opt.label}
						</button>
					))}
				</div>
			</div>
			<div className="flex items-center gap-4">
				<button
					onClick={onToday}
					className="hidden md:block px-4 py-2 text-sm font-medium border border-dark-surface-elevated rounded-lg hover:bg-dark-surface transition-all whitespace-nowrap"
				>
					Today
				</button>

				{/* Desktop Week Navigator */}
				<div className="flex items-center bg-dark-surface rounded-lg">
					<button
						onClick={() => onDayChange(-1)}
						className="p-2 rounded-md hover:bg-dark-surface-elevated transition-colors"
					>
						<IconChevronLeft size={18} />
					</button>
					<button
						onClick={onCalendarClick}
						className="flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors hover:bg-dark-surface-elevated"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content="Open calendar navigation"
					>
						<span className="text-lg font-semibold">
							{format(currentDate, "MMMM d, yyyy")}
						</span>
						<IconCalendar size={18} />
					</button>
					<button
						onClick={() => onDayChange(7)}
						className="p-2 rounded-md hover:bg-dark-surface-elevated transition-colors"
					>
						<IconChevronRight size={18} />
					</button>
				</div>
				{viewType !== "all" && (
					<button
						onClick={onAddTask}
						className="px-4 py-2 flex items-center gap-2 bg-sentient-blue hover:bg-sentient-blue-dark text-white font-semibold rounded-lg text-sm transition-colors"
					>
						<IconPlus size={16} />
						Add Task
					</button>
				)}
			</div>
		</header>
	)
}

export default TasksHeader
