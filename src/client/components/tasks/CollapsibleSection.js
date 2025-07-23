"use client"

import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@utils/cn"
import { IconChevronDown } from "@tabler/icons-react"

const CollapsibleSection = ({ title, count, children, isOpen, onToggle }) => {
	return (
		<motion.div layout className="mb-6">
			<button
				onClick={onToggle}
				className="w-full flex justify-between items-center p-3 hover:bg-[var(--color-primary-surface)]/50 rounded-lg transition-colors"
			>
				<h3 className="font-medium text-base text-[var(--color-text-primary)]">
					{title}{" "}
					<span className="text-sm text-neutral-400">({count})</span>
				</h3>
				<IconChevronDown
					className={cn(
						"transform transition-transform duration-300 text-neutral-400",
						isOpen ? "rotate-180" : "rotate-0"
					)}
					size={20}
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
						<div className="pt-2 space-y-3">{children}</div>
					</motion.div>
				)}
			</AnimatePresence>
		</motion.div>
	)
}

export default CollapsibleSection
