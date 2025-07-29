"use client"

import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@utils/cn"
import { IconChevronDown } from "@tabler/icons-react"

const CollapsibleSection = ({
	title,
	children,
	isOpen: defaultOpen = true
}) => {
	const [isOpen, setIsOpen] = useState(defaultOpen)

	const onToggle = () => setIsOpen(!isOpen)

	return (
		<motion.div layout className="mb-2">
			<button
				onClick={onToggle}
				className="w-full flex justify-between items-center p-2 hover:bg-neutral-800/50 rounded-lg transition-colors"
			>
				<div className="w-full text-left">{title}</div>
				<IconChevronDown
					className={cn(
						"transform transition-transform duration-300 text-neutral-400",
						isOpen ? "rotate-180" : "rotate-0"
					)}
					size={20}
				/>
			</button>
			<AnimatePresence initial={false}>
				{isOpen && (
					<motion.div
						initial={{ height: 0, opacity: 0 }}
						animate={{ height: "auto", opacity: 1 }}
						exit={{ height: 0, opacity: 0 }}
						transition={{ duration: 0.3, ease: "easeInOut" }}
						className="overflow-hidden"
					>
						<div className="pt-2">{children}</div>
					</motion.div>
				)}
			</AnimatePresence>
		</motion.div>
	)
}

export default CollapsibleSection
