// src/client/components/tasks/GCalEventCard.js
"use client"
import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { IconCalendarEvent } from "@tabler/icons-react"

const GCalEventCard = ({ event, onSelectTask }) => {
	const handleClick = (e) => {
		e.stopPropagation()
		// Renamed onSelectTask to handle both tasks and events
		onSelectTask(event)
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={handleClick}
			className={cn(
				"w-full p-2 rounded-md text-xs font-medium text-white cursor-pointer truncate",
				"bg-green-500/20 hover:bg-green-500/40 border-l-2 border-green-400"
			)}
			data-tooltip-id="tasks-tooltip"
			data-tooltip-content={`Google Calendar: ${event.summary}. Click for details.`}
		>
			<div className="flex items-center gap-2">
				<IconCalendarEvent size={12} className="flex-shrink-0" />
				<span className="truncate">{event.summary}</span>
			</div>
		</motion.div>
	)
}

export default GCalEventCard
