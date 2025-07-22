"use client"

import React, { useEffect } from "react"
import { motion } from "framer-motion"
import OrganizerEntryCard from "./TaskKanbanCard"
import TaskSearchResultCard from "./TaskSearchResultCard"

const SearchOverlay = ({
	query,
	results,
	onClose,
	onResultClick,
	tasksById,
	onEditEntry,
	onDeleteEntry,
	onDuplicateEntry
}) => {
	useEffect(() => {
		const handleKeyDown = (e) => {
			if (e.key === "Escape") {
				onClose()
			}
		}
		window.addEventListener("keydown", handleKeyDown)
		return () => window.removeEventListener("keydown", handleKeyDown)
	}, [onClose])

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			onClick={onClose}
			className="absolute inset-0 z-10 bg-black/60 backdrop-blur-sm"
		>
			<motion.div
				initial={{ opacity: 0, y: -20 }}
				animate={{ opacity: 1, y: 0 }}
				exit={{ opacity: 0, y: -20 }}
				className="mx-auto mt-24 max-w-3xl space-y-3"
				onClick={(e) => e.stopPropagation()}
			>
				{results.map((item) =>
					item.item_type === "tasks" ? (
						<OrganizerEntryCard
							key={item.block_id}
							item={item}
							linkedTask={tasksById[item.linked_task_id]}
							onViewEntry={() => onResultClick(item)}
							onEditEntry={onEditEntry}
							onDeleteEntry={onDeleteEntry}
							onDuplicateEntry={onDuplicateEntry}
						/>
					) : (
						<TaskSearchResultCard
							key={item.task_id}
							task={item}
							onSelect={() => onResultClick(item)}
						/>
					)
				)}
			</motion.div>
		</motion.div>
	)
}

export default SearchOverlay
