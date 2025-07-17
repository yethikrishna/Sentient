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
import { DndProvider } from "react-dnd"
import { HTML5Backend } from "react-dnd-html5-backend"
import DayColumn from "./DayColumn"

const WeeklyKanban = ({
	allTasks,
	onViewTask,
	onEditTask,
	onDeleteTask,
	onDuplicateTask,
	onApproveTask,
	onAnswerClarifications,
	onToggleEnableTask,
	onTaskDrop,
	viewDate
}) => {
	const visibleDays = useMemo(() => {
		return eachDayOfInterval({
			start: subDays(viewDate, 1),
			end: addDays(viewDate, 1)
		})
	}, [viewDate])

	const tasksByDate = useMemo(() => {
		const grouped = {}
		const weekDays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
		visibleDays.forEach((date) => {
			const dateString = format(date, "yyyy-MM-dd")
			grouped[dateString] = (allTasks || []).filter((task) => {
				const schedule = task.schedule
				if (!schedule) return false
				if (schedule.type === "once" && schedule.run_at) {
					return isSameDay(parseISO(schedule.run_at), date)
				}

				if (schedule.type === "recurring") {
					if (schedule.frequency === "daily") return true
					if (schedule.frequency === "weekly") {
						return schedule.days?.includes(weekDays[getDay(date)])
					}
				}
				return false
			})
		})
		return grouped
	}, [allTasks, visibleDays])

	return (
		<DndProvider backend={HTML5Backend}>
			<div
				className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full"
				style={{ minWidth: "900px" }}
			>
				{visibleDays.map((day, index) => (
					<DayColumn
						key={format(day, "yyyy-MM-dd")}
						date={day}
						tasks={tasksByDate[format(day, "yyyy-MM-dd")] || []}
						onViewTask={onViewTask}
						onEditTask={onEditTask}
						onDeleteTask={onDeleteTask}
						onDuplicateTask={onDuplicateTask}
						onApproveTask={onApproveTask}
						onAnswerClarifications={onAnswerClarifications}
						onToggleEnableTask={onToggleEnableTask}
						onTaskDrop={onTaskDrop}
					/>
				))}
			</div>
		</DndProvider>
	)
}

export default WeeklyKanban
