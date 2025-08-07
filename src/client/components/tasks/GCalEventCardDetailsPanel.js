// src/client/components/tasks/GCalEventCardDetailsPanel.js
"use client"
import React from "react"
import {
	IconX,
	IconCalendarEvent,
	IconClock,
	IconUsers,
	IconFileText,
	IconLink,
	IconPlus
} from "@tabler/icons-react"
import { format, parseISO } from "date-fns"
import { cn } from "@utils/cn"

const GCalEventDetailsPanel = ({ event, onClose, onCreateTask }) => {
	if (!event) return null

	const startTime = event.start ? format(parseISO(event.start), "p") : "N/A"
	const endTime = event.end ? format(parseISO(event.end), "p") : "N/A"
	const date = event.start
		? format(parseISO(event.start), "eeee, MMMM d")
		: "N/A"

	const DetailItem = ({ icon, label, children }) => (
		<div className="flex items-start gap-3">
			<div className="flex-shrink-0 text-neutral-400 mt-1">{icon}</div>
			<div className="flex-1">
				<p className="text-xs text-neutral-400">{label}</p>
				<div className="text-sm text-neutral-200 mt-0.5">
					{children}
				</div>
			</div>
		</div>
	)

	return (
		<aside
			className={cn(
				"w-full h-full bg-brand-black backdrop-blur-xl shadow-2xl md:border-l border-neutral-700/80 flex flex-col flex-shrink-0"
			)}
		>
			{/* --- HEADER --- */}
			<header className="flex items-start justify-between p-6 border-b border-neutral-700/50 flex-shrink-0">
				<div className="flex items-center gap-3">
					<IconCalendarEvent
						size={24}
						className="text-green-400 flex-shrink-0"
					/>
					<h2 className="text-xl font-bold text-white leading-snug">
						{event.summary || "Google Calendar Event"}
					</h2>
				</div>
				<button
					onClick={onClose}
					className="ml-4 p-2 rounded-full text-neutral-400 hover:bg-neutral-700 hover:text-white"
				>
					<IconX size={20} />
				</button>
			</header>

			{/* --- CONTENT --- */}
			<main className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
				<DetailItem icon={<IconClock size={16} />} label="Time">
					<p>
						{date}, {startTime} - {endTime}
					</p>
				</DetailItem>

				{event.description && (
					<DetailItem
						icon={<IconFileText size={16} />}
						label="Description"
					>
						<p className="whitespace-pre-wrap">
							{event.description}
						</p>
					</DetailItem>
				)}

				{event.attendees && event.attendees.length > 0 && (
					<DetailItem
						icon={<IconUsers size={16} />}
						label="Attendees"
					>
						<div className="flex flex-col gap-1">
							{event.attendees.map((email, index) => (
								<span key={index} className="text-xs font-mono">
									{email}
								</span>
							))}
						</div>
					</DetailItem>
				)}

				{event.url && (
					<DetailItem icon={<IconLink size={16} />} label="Link">
						<a
							href={event.url}
							target="_blank"
							rel="noopener noreferrer"
							className="text-blue-400 hover:underline"
						>
							View on Google Calendar
						</a>
					</DetailItem>
				)}
			</main>

			{/* --- FOOTER --- */}
			<footer className="p-4 border-t border-neutral-700/50 flex-shrink-0 bg-brand-gray/50">
				<button
					onClick={() => onCreateTask(event)}
					className="w-full flex items-center justify-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors bg-brand-orange hover:bg-brand-orange/80 text-brand-black font-semibold"
				>
					<IconPlus size={16} />
					<span>Create Task from this Event</span>
				</button>
			</footer>
		</aside>
	)
}

export default GCalEventDetailsPanel
