"use client"
import React, { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
	format,
	startOfMonth,
	endOfMonth,
	startOfWeek,
	endOfWeek,
	eachDayOfInterval,
	isSameMonth,
	isToday,
	addMonths,
	subMonths,
	isSameDay
} from "date-fns"
import {
	IconChevronLeft,
	IconChevronRight,
	IconPlus,
	IconDots
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import TaskCardCalendar from "./TaskCardCalendar"

const CalendarDayCell = ({
	day,
	tasks,
	isCurrentMonth,
	onSelectTask,
	onDayClick,
	onShowMoreClick
}) => {
	const [isHovered, setIsHovered] = useState(false)
	const firstTask = tasks[0]
	const hasMoreTasks = tasks.length > 1

	return (
		<div
			onMouseEnter={() => setIsHovered(true)}
			onMouseLeave={() => setIsHovered(false)}
			className={cn(
				"border-r border-b border-neutral-800 p-2 flex flex-col gap-1 overflow-hidden relative min-h-[120px]",
				!isCurrentMonth && "bg-neutral-900/50",
				"hover:bg-neutral-800/70"
			)}
		>
			<div className="flex justify-between items-center">
				<span
					className={cn(
						"font-semibold text-sm",
						isToday(day)
							? "text-sentient-blue"
							: "text-neutral-300",
						!isCurrentMonth && "text-neutral-600"
					)}
				>
					{format(day, "d")}
				</span>
				<AnimatePresence>
					{isHovered && (
						<motion.button
							initial={{ opacity: 0, scale: 0.8 }}
							animate={{ opacity: 1, scale: 1 }}
							exit={{ opacity: 0, scale: 0.8 }}
							onClick={(e) => {
								e.stopPropagation()
								onDayClick(day)
							}}
							className="p-1 rounded-full hover:bg-neutral-700"
						>
							<IconPlus size={16} />
						</motion.button>
					)}
				</AnimatePresence>
			</div>
			<div
				className="space-y-1 flex-1 cursor-pointer"
				onClick={() => onShowMoreClick(day)}
			>
				{firstTask && (
					<TaskCardCalendar
						task={firstTask}
						onSelectTask={onSelectTask}
					/>
				)}
				{hasMoreTasks && (
					<div className="w-full text-center text-xs text-neutral-400 p-1 rounded-md hover:bg-neutral-700/50">
						<IconDots size={16} className="mx-auto" />
					</div>
				)}
			</div>
		</div>
	)
}

const CalendarView = ({ tasks, onSelectTask, onDayClick, onShowMoreClick }) => {
	const [currentMonth, setCurrentMonth] = useState(new Date())

	const monthStart = startOfMonth(currentMonth)
	const monthEnd = endOfMonth(currentMonth)
	const daysInGrid = eachDayOfInterval({
		start: startOfWeek(monthStart),
		end: endOfWeek(monthEnd)
	})

	const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1))
	const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1))

	return (
		<div className="p-6 h-full flex flex-col">
			<header className="flex items-center justify-between mb-4">
				<h2 className="text-xl font-semibold text-white">
					{format(currentMonth, "MMMM yyyy")}
				</h2>
				<div className="flex items-center gap-2">
					<button
						onClick={prevMonth}
						className="p-2 rounded-full hover:bg-neutral-800"
					>
						<IconChevronLeft size={20} />
					</button>
					<button
						onClick={nextMonth}
						className="p-2 rounded-full hover:bg-neutral-800"
					>
						<IconChevronRight size={20} />
					</button>
				</div>
			</header>
			<div className="grid grid-cols-7 text-center text-sm text-neutral-400 border-b border-neutral-800 pb-2">
				{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(
					(day) => (
						<div key={day}>{day}</div>
					)
				)}
			</div>
			<div className="grid grid-cols-7 grid-rows-5 flex-1">
				{daysInGrid.map((day) => {
					const tasksForDay = tasks.filter((task) =>
						isSameDay(task.scheduled_date, day)
					)
					return (
						<CalendarDayCell
							key={day.toString()}
							day={day}
							tasks={tasksForDay}
							isCurrentMonth={isSameMonth(day, currentMonth)}
							onSelectTask={onSelectTask}
							onDayClick={onDayClick}
							onShowMoreClick={onShowMoreClick}
						/>
					)
				})}
			</div>
		</div>
	)
}

export default CalendarView
