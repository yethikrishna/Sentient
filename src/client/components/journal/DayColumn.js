"use client"

import React, { useMemo } from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { isToday, isSameDay, subDays, addDays, format } from "date-fns"
import { IconPlus } from "@tabler/icons-react"
import InlineAddEntry from "./InlineAddEntry"
import JournalEntryCard from "./JournalEntryCard"

const DayColumn = ({
	day,
	items,
	isAdding,
	onStartAdd,
	onEndAdd,
	onViewEntry,
	onEditEntry,
	onDeleteEntry,
	onDuplicateEntry,
	tasksById
}) => {
	const isCurrentDay = isToday(day)
	const isYesterday = isSameDay(day, subDays(new Date(), 1))
	const isTomorrow = isSameDay(day, addDays(new Date(), 1))

	const dayLabel = useMemo(() => {
		if (isCurrentDay) return "Today"
		if (isYesterday) return "Yesterday"
		if (isTomorrow) return "Tomorrow"
		return format(day, "eee")
	}, [day, isCurrentDay, isYesterday, isTomorrow])

	return (
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			transition={{ duration: 0.4, ease: "easeOut" }}
			className="flex flex-col bg-[var(--color-primary-surface)]/20 rounded-2xl h-full"
		>
			<div className="flex justify-between items-center p-4 border-b border-[var(--color-primary-surface)]/50">
				<h3 className="font-semibold text-lg flex items-center gap-2">
					<span
						className={cn(
							isCurrentDay && "text-[var(--color-accent-blue)]"
						)}
					>
						{dayLabel}
					</span>
					<span
						className={cn(
							"text-lg font-bold text-neutral-400",
							isCurrentDay && "text-white"
						)}
					>
						{format(day, "d MMM")}
					</span>
				</h3>
			</div>
			<div className="p-3 space-y-3 flex-1 overflow-y-auto custom-scrollbar">
				{items.map((item) => (
					<JournalEntryCard
						key={item.block_id}
						item={item}
						linkedTask={tasksById[item.linked_task_id]}
						onViewEntry={onViewEntry}
						onEditEntry={onEditEntry}
						onDeleteEntry={onDeleteEntry}
						onDuplicateEntry={onDuplicateEntry}
					/>
				))}
				{items.length === 0 && (
					<div className="text-center py-10 text-sm text-[var(--color-text-muted)]">
						No entries.
					</div>
				)}
			</div>
			<div className="p-3 mt-auto border-t border-[var(--color-primary-surface)]/50">
				{isAdding ? (
					<InlineAddEntry
						day={day}
						onSave={onEndAdd}
						onCancel={() => onEndAdd()}
					/>
				) : (
					<button
						onClick={onStartAdd}
						data-tooltip-id="journal-help"
						data-tooltip-content="Add a new entry for this day. This can be a simple note or a task for Sentient to process."
						className="w-full flex items-center justify-center gap-2 p-3 rounded-lg text-neutral-400 hover:bg-[var(--color-primary-surface)] hover:text-white transition-colors"
					>
						<IconPlus size={18} />
						<span className="text-sm font-medium">Add a card</span>
					</button>
				)}
			</div>
		</motion.div>
	)
}

export default DayColumn
