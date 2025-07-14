"use client"

import React from "react"
import { cn } from "@utils/cn"

const SidebarTabButton = ({
	label,
	icon,
	isActive,
	onClick,
	tooltipContent
}) => {
	return (
		<button
			onClick={onClick}
			className={cn(
				"p-3 rounded-lg transition-colors w-full flex flex-col items-center",
				isActive
					? "bg-blue-500/30 text-white"
					: "hover:bg-[var(--color-primary-surface)] text-neutral-400 hover:text-white"
			)}
			data-tooltip-id="journal-help"
			data-tooltip-content={tooltipContent || label}
		>
			{React.cloneElement(icon, { className: "transition-transform" })}
		</button>
	)
}

export default SidebarTabButton
