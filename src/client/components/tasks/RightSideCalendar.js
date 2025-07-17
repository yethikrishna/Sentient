"use client"

import React, { useState, useEffect } from "react"
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
	subDays,
	addDays,
	isToday,
	isWithinInterval
} from "date-fns"
import { cn } from "@utils/cn"
import { IconChevronLeft, IconChevronRight } from "@tabler/icons-react"
import { weekDays } from "./constants"

const RightSideCalendar = ({ viewDate, onDateChange, itemsByDate }) => {
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
	const viewStart = subDays(viewDate, 1)
	const viewEnd = addDays(viewDate, 1)

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
					const isInView = isWithinInterval(day, {
						start: viewStart,
						end: viewEnd
					})
					const dayTasks =
						(itemsByDate &&
							itemsByDate[format(day, "yyyy-MM-dd")]) ||
						[]
					const hasEntry = dayTasks.length > 0
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
								isInView &&
									"bg-[var(--color-accent-blue)]/20 text-white",
								isSameDay(day, viewDate) &&
									"bg-[var(--color-accent-blue)]/40 font-bold",
								"hover:bg-[var(--color-primary-surface)]"
							)}
						>
							{format(day, "d")}
							{hasEntry && (
								<span className="absolute bottom-1.5 h-1 w-1 bg-[var(--color-accent-purple)] rounded-full"></span>
							)}
						</button>
					)
				})}
			</div>
			<div className="mt-auto pt-6 text-sm text-gray-500">
				<p className="font-semibold text-gray-400 mb-2">Legend:</p>
				<div className="flex items-center gap-2 mb-1">
					<span className="h-2 w-2 rounded-full bg-[var(--color-accent-purple)]"></span>{" "}
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
					Selected View
				</div>
			</div>
		</div>
	)
}

export default RightSideCalendar
