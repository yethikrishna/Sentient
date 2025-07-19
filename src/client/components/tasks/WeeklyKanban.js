"use client"

import React, { useMemo } from "react"
import {
	format,
	addDays,
	subDays,
	eachDayOfInterval,
	isSameDay,
	parseISO,
	getDay
} from "date-fns"
import DayColumn from "./DayColumn"

const WeeklyKanban = ({
	tasks,
	recurringTasks,
	currentDate,
	onTaskDrop,
	...handlers
}) => {
	// A week is now 7 days centered on the current date
	const visibleDays = useMemo(() => {
		return eachDayOfInterval({
			start: subDays(currentDate, 3),
			end: addDays(currentDate, 3)
		})
	}, [currentDate])

	const tasksByDate = useMemo(() => {
		const grouped = {}
		tasks.forEach((task) => {
			if (task.schedule?.type === "once" && task.schedule.run_at) {
				const date = parseISO(task.schedule.run_at)
				const dateString = format(date, "yyyy-MM-dd")
				if (!grouped[dateString]) grouped[dateString] = []
				grouped[dateString].push(task)
			}
		})
		return grouped
	}, [tasks])

	const recurringTasksByDate = useMemo(() => {
		const grouped = {}
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
			visibleDays.forEach((date) => {
				const dayOfWeek = dayNames[getDay(date)]
				if (
					task.schedule.frequency === "daily" ||
					(task.schedule.frequency === "weekly" &&
						task.schedule.days.includes(dayOfWeek))
				) {
					const dateString = format(date, "yyyy-MM-dd")
					if (!grouped[dateString]) grouped[dateString] = []
					grouped[dateString].push(task)
				}
			})
		})
		return grouped
	}, [recurringTasks, visibleDays])

	return (
		<div className="h-full overflow-x-auto custom-scrollbar pb-4 -mx-4 px-4 md:-mx-6 md:px-6 ">
			<div className="flex gap-4 h-full" style={{ minWidth: "2100px" }}>
				{visibleDays.map((day) => (
					<DayColumn
						key={format(day, "yyyy-MM-dd")}
						date={day}
						tasks={tasksByDate[format(day, "yyyy-MM-dd")] || []}
						recurringTasks={
							recurringTasksByDate[format(day, "yyyy-MM-dd")] ||
							[]
						}
						onTaskDrop={onTaskDrop}
						{...handlers}
					/>
				))}
			</div>
		</div>
	)
}

export default WeeklyKanban
