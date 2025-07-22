"use client"

import React, { useState, useMemo } from "react"
import {
	format,
	startOfMonth,
	endOfMonth,
	startOfWeek,
	endOfWeek,
	eachDayOfInterval,
	isSameMonth,
	isSameDay,
	isToday,
	parseISO,
	getDay
} from "date-fns"
import { cn } from "@utils/cn"
import TaskPill from "./TaskPill"

const DayCell = ({ day, isCurrentMonth, tasks, onViewDetails }) => {
	const maxPills = 2
	const visibleTasks = tasks.slice(0, maxPills)
	const hiddenCount = tasks.length - maxPills

	return (
		<div
			className={cn(
				"p-2 border-t border-r border-dark-surface-elevated flex flex-col overflow-hidden min-h-[120px]",
				!isCurrentMonth && "bg-dark-surface/30"
			)}
		>
			<span
				className={cn(
					"font-semibold",
					isToday(day)
						? "bg-sentient-blue text-white rounded-full h-6 w-6 flex items-center justify-center"
						: isCurrentMonth
							? "text-white"
							: "text-neutral-500"
				)}
			>
				{format(day, "d")}
			</span>
			<div className="mt-2 space-y-1 overflow-hidden">
				{visibleTasks.map((task) => (
					<TaskPill
						key={task.task_id}
						task={task}
						onClick={() => onViewDetails(task)}
					/>
				))}
				{hiddenCount > 0 && (
					<button className="text-xs text-neutral-400 hover:underline text-left">
						+{hiddenCount} more
					</button>
				)}
			</div>
		</div>
	)
}

const MonthlyView = ({
	tasks = [],
	recurringTasks = [],
	currentDate,
	onViewDetails
}) => {
	const monthStart = startOfMonth(currentDate)
	const monthEnd = endOfMonth(currentDate)
	const daysInGrid = eachDayOfInterval({
		start: startOfWeek(monthStart),
		end: endOfWeek(monthEnd)
	})

	const allTasksByDate = useMemo(() => {
		const grouped = {}
		tasks.forEach((task) => {
			if (task.schedule?.type === "once" && task.schedule.run_at) {
				const dateStr = format(
					parseISO(task.schedule.run_at),
					"yyyy-MM-dd"
				)
				if (!grouped[dateStr]) grouped[dateStr] = []
				grouped[dateStr].push(task)
			}
		})
		const dayNames = [
			"Sunday",
			"Monday",
			"Tuesday",
			"Wednesday",
			"Thursday",
			"Friday",
			"Saturday"
		]
		recurringTasks.forEach((task) => {
			daysInGrid.forEach((date) => {
				const dayOfWeek = dayNames[getDay(date)]
				if (
					task.schedule.frequency === "daily" ||
					(task.schedule.frequency === "weekly" &&
						task.schedule.days.includes(dayOfWeek))
				) {
					const dateStr = format(date, "yyyy-MM-dd")
					if (!grouped[dateStr]) grouped[dateStr] = []
					grouped[dateStr].push(task)
				}
			})
		})
		return grouped
	}, [tasks, recurringTasks, daysInGrid])

	return (
		<div className="h-full flex flex-col bg-dark-surface rounded-lg border border-dark-surface-elevated overflow-hidden">
			<div className="overflow-auto custom-scrollbar">
				<div className="min-w-[800px]">
					<div className="grid grid-cols-7 text-center font-semibold text-neutral-400 border-b border-dark-surface-elevated">
						{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(
							(day) => (
								<div key={day} className="py-2">
									{day}
								</div>
							)
						)}
					</div>
					<div className="grid grid-cols-7 grid-rows-6 flex-1">
						{daysInGrid.map((day, i) => (
							<DayCell
								key={i}
								day={day}
								isCurrentMonth={isSameMonth(day, currentDate)}
								tasks={
									allTasksByDate[format(day, "yyyy-MM-dd")] ||
									[]
								}
								onViewDetails={onViewDetails}
							/>
						))}
					</div>
				</div>
			</div>
		</div>
	)
}

export default MonthlyView
