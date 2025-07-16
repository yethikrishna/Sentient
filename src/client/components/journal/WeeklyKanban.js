"use client"

import React, { useMemo } from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { subDays, addDays, format } from "date-fns"
import DayColumn from "./DayColumn"

const WeeklyKanban = ({
	viewDate,
	itemsByDate,
	tasksById,
	addingToDay,
	setAddingToDay,
	onViewEntry,
	onEditEntry,
	onDeleteEntry,
	onDuplicateEntry,
	onDataChange
}) => {
	const days = useMemo(
		() => [subDays(viewDate, 1), viewDate, addDays(viewDate, 1)],
		[viewDate]
	)

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			transition={{ duration: 0.5, delay: 0.1 }}
			className="grid grid-cols-1 md:grid-cols-3 gap-4 flex-1 h-full"
		>
			{days.map((day) => (
				<div
					key={format(day, "yyyy-MM-dd")}
					className={cn(
						"h-full",
						format(day, "yyyy-MM-dd") !==
							format(viewDate, "yyyy-MM-dd") && "hidden md:block"
					)}
				>
					<DayColumn
						day={day}
						items={itemsByDate[format(day, "yyyy-MM-dd")] || []}
						tasksById={tasksById}
						isAdding={addingToDay === format(day, "yyyy-MM-dd")}
						onStartAdd={() =>
							setAddingToDay(format(day, "yyyy-MM-dd"))
						}
						onEndAdd={() => {
							setAddingToDay(null)
							onDataChange()
						}}
						onViewEntry={onViewEntry}
						onEditEntry={onEditEntry}
						onDeleteEntry={onDeleteEntry}
						onDuplicateEntry={onDuplicateEntry}
					/>
				</div>
			))}
		</motion.div>
	)
}

export default WeeklyKanban
