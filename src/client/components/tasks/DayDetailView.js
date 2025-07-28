"use client"
import React, { useState, useEffect, useRef } from "react"
import { format, getHours, getMinutes, parseISO, isToday } from "date-fns"
import { cn } from "@utils/cn"
import TaskCardDayView from "./TaskCardDayView"
import { IconX } from "@tabler/icons-react"

const DayDetailView = ({ date, tasks, onSelectTask, onClose }) => {
	const [currentTime, setCurrentTime] = useState(new Date())
	const timelineRef = useRef(null)

	useEffect(() => {
		const timer = setInterval(() => setCurrentTime(new Date()), 60000) // Update every minute
		return () => clearInterval(timer)
	}, [])

	const hours = Array.from({ length: 24 }, (_, i) => i)

	const allDayTasks = tasks.filter(
		(t) => !t.schedule?.run_at || !t.schedule.run_at.includes("T")
	)
	const timedTasks = tasks.filter(
		(t) => t.schedule?.run_at && t.schedule.run_at.includes("T")
	)

	const getTopPosition = (isoString) => {
		try {
			const date = parseISO(isoString)
			const hours = getHours(date)
			const minutes = getMinutes(date)
			// Calculate percentage of the total height (24 hours * 4rem/hour)
			const totalHeight = 24 * 64 // 24 hours * 16 (h-16) * 4 (rem-to-px)
			const topInPixels = (hours + minutes / 60) * 64
			return topInPixels
		} catch (e) {
			return 0
		}
	}

	const timeIndicatorTop =
		(getHours(currentTime) + getMinutes(currentTime) / 60) * 64

	return (
		<div className="h-full flex flex-col bg-neutral-900 text-white">
			<header className="p-4 border-b border-neutral-800 flex-shrink-0 flex justify-between items-center">
				<h3 className="text-lg font-semibold">
					{format(date, "eeee, MMMM d")}
				</h3>
				<button
					onClick={onClose}
					className="p-1 rounded-full hover:bg-neutral-700"
				>
					<IconX size={18} />
				</button>
			</header>

			<div className="flex-1 overflow-y-auto custom-scrollbar">
				{/* All-day tasks section */}
				<div className="p-4 border-b border-neutral-800">
					<div className="space-y-2">
						{allDayTasks.length > 0 ? (
							allDayTasks.map((task) => (
								<TaskCardDayView
									key={task.instance_id}
									task={task}
									onSelectTask={onSelectTask}
								/>
							))
						) : (
							<p className="text-xs text-neutral-500">
								No all-day tasks.
							</p>
						)}
					</div>
				</div>

				{/* Hourly timeline */}
				<div
					className="relative"
					ref={timelineRef}
					style={{ height: `${24 * 64}px` }}
				>
					{/* Current time indicator */}
					{isToday(date) && (
						<div
							className="absolute w-full z-10"
							style={{ top: `${timeIndicatorTop}px` }}
						>
							<div className="flex items-center">
								<div className="w-2 h-2 rounded-full bg-red-500 -ml-1"></div>
								<div className="h-[1px] w-full bg-red-500"></div>
							</div>
						</div>
					)}

					{/* Timed tasks */}
					<div className="absolute inset-0">
						{timedTasks.map((task) => (
							<div
								key={task.instance_id}
								className="absolute w-full pr-4 pl-16"
								style={{
									top: `${getTopPosition(task.schedule.run_at)}px`
								}}
							>
								<TaskCardDayView
									task={task}
									onSelectTask={onSelectTask}
								/>
							</div>
						))}
					</div>

					{/* Hour lines */}
					{hours.map((hour) => (
						<div
							key={hour}
							className="flex h-16 border-b border-neutral-800"
						>
							<div className="w-16 text-right pr-2 pt-1 text-xs text-neutral-500">
								{format(new Date(0, 0, 0, hour), "ha")}
							</div>
							<div className="flex-1"></div>
						</div>
					))}
				</div>
			</div>
		</div>
	)
}

export default DayDetailView
