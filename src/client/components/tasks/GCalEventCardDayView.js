// src/client/components/tasks/GCalEventCardDayView.js
"use client"
import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { IconCalendarEvent } from "@tabler/icons-react"

const GCalEventCardDayView = ({ event, onSelectTask: onSelectItem }) => {
	const handleClick = (e) => {
		e.stopPropagation()
		if (onSelectItem) {
			onSelectItem(event)
		}
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={handleClick}
			className={cn(
				"p-2 rounded-md text-sm font-medium text-white cursor-pointer",
				"bg-green-500/30 border-l-2 border-green-400 hover:bg-green-500/40"
			)}
			data-tooltip-id="tasks-tooltip"
			data-tooltip-content={`Google Calendar: ${event.summary}. Click for details.`}
		>
			<div className="flex items-center gap-2">
				<IconCalendarEvent size={14} className="flex-shrink-0" />
				<p className="truncate">{event.summary}</p>
			</div>
		</motion.div>
	)
}

export default GCalEventCardDayView
