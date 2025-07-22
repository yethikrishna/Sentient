"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
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
	isToday,
	addYears
} from "date-fns"
import { cn } from "@utils/cn"
import {
	IconChevronLeft,
	IconChevronRight,
	IconX,
	IconChevronsLeft,
	IconChevronsRight
} from "@tabler/icons-react"

const CalendarGrid = ({ selectedDate, onDateSelect, month, setMonth }) => {
	const monthStart = startOfMonth(month)
	const monthEnd = endOfMonth(month)
	const daysInMonth = eachDayOfInterval({
		start: startOfWeek(monthStart),
		end: endOfWeek(monthEnd)
	})

	return (
		<div>
			<div className="flex items-center justify-between mb-4">
				<div className="flex items-center gap-1">
					<button
						onClick={() => setMonth(addYears(month, -1))}
						className="p-2 rounded-lg hover:bg-dark-surface"
					>
						<IconChevronsLeft size={16} />
					</button>
					<button
						onClick={() => setMonth(addMonths(month, -1))}
						className="p-2 rounded-lg hover:bg-dark-surface"
					>
						<IconChevronLeft size={16} />
					</button>
				</div>
				<h3 className="text-lg font-semibold text-white text-center">
					{format(month, "MMMM yyyy")}
				</h3>
				<div className="flex items-center gap-1">
					<button
						onClick={() => setMonth(addMonths(month, 1))}
						className="p-2 rounded-lg hover:bg-dark-surface"
					>
						<IconChevronRight size={16} />
					</button>
					<button
						onClick={() => setMonth(addYears(month, 1))}
						className="p-2 rounded-lg hover:bg-dark-surface"
					>
						<IconChevronsRight size={16} />
					</button>
				</div>
			</div>
			<div className="grid grid-cols-7 gap-y-2 text-center text-xs text-neutral-400 mb-3">
				{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(
					(day) => (
						<div key={day}>{day}</div>
					)
				)}
			</div>
			<div className="grid grid-cols-7 gap-1">
				{daysInMonth.map((day, i) => (
					<button
						key={i}
						onClick={() => onDateSelect(day)}
						className={cn(
							"h-10 w-10 flex items-center justify-center rounded-full transition-colors",
							!isSameMonth(day, month) && "text-neutral-600",
							isToday(day) && "ring-2 ring-sentient-blue",
							isSameDay(day, selectedDate) &&
								"bg-sentient-blue font-bold text-white",
							"hover:bg-dark-surface"
						)}
					>
						{format(day, "d")}
					</button>
				))}
			</div>
		</div>
	)
}

const CalendarNavModal = ({ currentDate, onDateSelect, onClose }) => {
	const [month, setMonth] = useState(startOfMonth(currentDate))

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={onClose}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-dark-surface p-6 rounded-2xl shadow-xl w-full max-w-sm border border-dark-surface-elevated"
			>
				<div className="flex justify-end mb-2">
					<button
						onClick={onClose}
						className="p-1 rounded-full hover:bg-dark-surface-elevated"
					>
						<IconX size={20} />
					</button>
				</div>
				<CalendarGrid
					selectedDate={currentDate}
					onDateSelect={onDateSelect}
					month={month}
					setMonth={setMonth}
				/>
			</motion.div>
		</motion.div>
	)
}

export default CalendarNavModal
