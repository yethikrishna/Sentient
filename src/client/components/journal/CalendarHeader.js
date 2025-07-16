"use client"

import React from "react"
import { motion } from "framer-motion"
import { format, subDays, addDays } from "date-fns"
import {
	IconSearch,
	IconChevronLeft,
	IconChevronRight,
	IconHelpCircle
} from "@tabler/icons-react"

const CalendarHeader = ({
	viewDate,
	onWeekChange,
	onDayChange,
	onToday,
	searchQuery,
	setSearchQuery
}) => {
	const viewStart = subDays(viewDate, 1)
	const viewEnd = addDays(viewDate, 1)
	return (
		<motion.header
			initial={{ y: -20, opacity: 0 }}
			animate={{ y: 0, opacity: 1 }}
			transition={{ duration: 0.6, ease: "easeOut" }}
			className="flex items-center justify-between p-4 md:p-6 border-b border-[var(--color-primary-surface)]/50 backdrop-blur-md bg-[var(--color-primary-background)]/90 shrink-0"
		>
			<div className="flex items-center gap-4">
				<h1 className="text-3xl font-semibold text-white hidden lg:block">
					Organizer
				</h1>
				<div className="relative w-full max-w-xs">
					<IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
					<input
						type="text"
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						placeholder="Search journal & tasks..."
						className="w-full bg-neutral-800/50 border border-neutral-700/80 rounded-lg py-2 pl-10 pr-4 transition-colors focus:border-[var(--color-accent-blue)]"
					/>
				</div>
				<button
					data-tooltip-id="journal-help"
					data-tooltip-content="Search your journal entries or use Ctrl + ←/→ to navigate between days."
					className="p-1.5 rounded-full text-neutral-500 hover:text-white hover:bg-[var(--color-primary-surface)] pulse-glow-animation"
				>
					<IconHelpCircle size={22} />
				</button>
			</div>
			<div className="flex items-center gap-2 md:gap-6">
				<motion.button // eslint-disable-line
					onClick={onToday}
					whileHover={{ scale: 1.05, y: -2 }}
					whileTap={{ scale: 0.95 }}
					className="xs:hidden md:flex px-4 md:px-6 py-2 text-sm font-medium border border-[var(--color-primary-surface-elevated)] rounded-xl hover:bg-[var(--color-primary-surface)] hover:border-[var(--color-accent-blue)]/30 transition-all duration-300 backdrop-blur-sm"
				>
					Today
				</motion.button>
				{/* Desktop Week Navigator */}
				<div className="hidden md:flex items-center bg-[var(--color-primary-surface)]/50 rounded-2xl p-1 backdrop-blur-sm">
					<button
						onClick={() => onWeekChange(-1)}
						className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95"
					>
						<IconChevronLeft size={18} />
					</button>
					<motion.h2
						key={format(viewStart, "yyyy-MM-dd")}
						initial={{ opacity: 0, y: 10 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ duration: 0.3 }}
						className="w-64 text-center text-lg font-semibold px-4"
					>
						{format(viewStart, "MMMM d")} -{" "}
						{format(viewEnd, "d, yyyy")}
					</motion.h2>
					<button
						onClick={() => onWeekChange(1)}
						className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95"
					>
						<IconChevronRight size={18} />
					</button>
				</div>
				{/* Mobile Day Navigator */}
				<div className="flex items-center bg-[var(--color-primary-surface)]/50 rounded-2xl p-1 backdrop-blur-sm">
					<div className="md:hidden flex items-center">
						<button
							onClick={() => onDayChange(-1)}
							className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95"
						>
							<IconChevronLeft size={18} />
						</button>
						<motion.h2
							key={format(viewDate, "yyyy-MM-dd")}
							initial={{ opacity: 0, y: 10 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.3 }}
							className="w-32 text-center text-base font-semibold px-2"
						>
							{format(viewDate, "MMMM d, yyyy")}
						</motion.h2>
						<button
							onClick={() => onDayChange(1)}
							className="p-3 rounded-xl hover:bg-[var(--color-primary-surface)] transition-all duration-300 hover:scale-110 active:scale-95"
						>
							<IconChevronRight size={18} />
						</button>
					</div>
				</div>
			</div>
		</motion.header>
	)
}

export default CalendarHeader
