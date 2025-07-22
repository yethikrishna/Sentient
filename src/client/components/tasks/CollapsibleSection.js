"use client"

import React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@utils/cn"
import { IconChevronDown } from "@tabler/icons-react"

const CollapsibleSection = ({
	title,
	count,
	isOpen,
	toggleOpen,
	children
}) => {
	return (
		<div>
			<button
				onClick={toggleOpen}
				className="w-full flex justify-between items-center py-2 px-1 text-left hover:bg-dark-surface/50 rounded-lg transition-colors"
			>
				<h2 className="text-lg font-semibold text-neutral-200 flex items-center gap-2">
					{title} ({count})
				</h2>
				<IconChevronDown
					className={cn(
						"transform transition-transform duration-200",
						isOpen ? "rotate-180" : "rotate-0"
					)}
				/>
			</button>
			<AnimatePresence>
				{isOpen && (
					<motion.div
						initial={{ height: 0, opacity: 0 }}
						animate={{ height: "auto", opacity: 1 }}
						exit={{ height: 0, opacity: 0 }}
						transition={{ duration: 0.3, ease: "easeInOut" }}
						className="overflow-hidden"
					>
						<div className="space-y-2 pt-2 pb-2">{children}</div>
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	)
}

export default CollapsibleSection
