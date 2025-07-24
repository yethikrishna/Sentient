"use client"

import React from "react"
import { IconHelpCircle } from "@tabler/icons-react"

const TasksHeader = ({ onOpenDemo }) => {
	return (
		<header className="flex flex-wrap items-center justify-between gap-4 px-4 sm:px-6 py-4 border-b border-[var(--color-primary-surface)] bg-dark-surface">
			<h1 className="text-2xl sm:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-br from-white to-neutral-400 py-1">
				Tasks
			</h1>

			<div className="flex items-center gap-3 shrink-0">
				<button
					onClick={onOpenDemo}
					className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] bg-[var(--color-primary-surface)] hover:bg-[var(--color-primary-surface-elevated)] rounded-lg border border-[var(--color-primary-surface)] hover:border-[var(--color-accent-blue)] transition-all duration-200"
					data-tooltip-id="tasks-tooltip"
					data-tooltip-content="Interactive Walkthrough"
				>
					<IconHelpCircle size={16} />
					<span>Help</span>
				</button>
			</div>
		</header>
	)
}

export default TasksHeader
