"use client"

import React from "react"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import { IconRepeat } from "@tabler/icons-react"

const TaskPill = ({ task, onClick }) => {
	const isRecurring = task.schedule?.type === "recurring"
	return (
		<motion.div
			onClick={onClick}
			className="text-xs p-1 bg-sentient-blue/20 text-sentient-blue rounded cursor-pointer whitespace-nowrap overflow-hidden text-ellipsis flex items-center gap-1"
			whileHover={{ scale: 1.05, backgroundColor: "#4a9eff40" }}
		>
			{isRecurring && <IconRepeat size={12} />}
			<span className="truncate">{task.description}</span>
		</motion.div>
	)
}

export default TaskPill
