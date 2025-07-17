"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import toast from "react-hot-toast"
import { IconX, IconTrash, IconPencil, IconLoader } from "@tabler/icons-react"
import TaskDetailsContent from "./TaskDetailsContent"

const EntryDetailsModal = ({
	block,
	task,
	onClose,
	startInEditMode,
	onDataChange,
	onDeleteRequest
}) => {
	const [isEditing, setIsEditing] = useState(startInEditMode)
	const [content, setContent] = useState(block.content)
	const [isSaving, setIsSaving] = useState(false)

	const handleSave = async () => {
		if (content === block.content) {
			setIsEditing(false)
			return
		}
		setIsSaving(true)
		try {
			const response = await fetch(
				`/api/organizer?blockId=${block.block_id}`,
				{
					method: "PUT",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ content: content })
				}
			)
			if (!response.ok) throw new Error("Failed to save entry.")
			toast.success("Entry updated!")
			onDataChange()
			setIsEditing(false)
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSaving(false)
		}
	}

	const handleDelete = () => {
		onClose() // Close this modal first
		onDeleteRequest(block) // Then trigger the confirmation modal
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
			onClick={onClose}
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-2xl border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="flex justify-between items-center mb-4 flex-shrink-0">
					<h3 className="text-xl font-semibold">Organizer Entry</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-2 space-y-4">
					{isEditing ? (
						<textarea
							value={content}
							onChange={(e) => setContent(e.target.value)}
							className="w-full bg-neutral-800/50 p-3 rounded-lg border border-neutral-700 min-h-[150px] focus:border-blue-500"
						/>
					) : (
						<p className="text-base whitespace-pre-wrap p-3 bg-neutral-800/20 rounded-lg">
							{content}
						</p>
					)}

					{task && (
						<div className="pt-4 border-t border-neutral-700/80">
							<h4 className="text-lg font-semibold mb-3">
								Linked Task Details
							</h4>
							<TaskDetailsContent task={task} />
						</div>
					)}
				</div>
				<div className="flex justify-between items-center mt-6 pt-4 border-t border-neutral-700 flex-shrink-0">
					{!block.isRecurring && (
						<button
							onClick={handleDelete}
							className="py-2 px-4 rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/40 text-sm font-semibold flex items-center gap-2"
						>
							<IconTrash size={16} /> Delete Entry
						</button>
					)}
					<div className="flex-grow"></div>
					<div className="flex gap-4">
						{isEditing ? (
							<>
								<button
									onClick={() => {
										setIsEditing(false)
										setContent(block.content)
									}}
									className="py-2 px-5 rounded-lg bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-sm"
								>
									Cancel
								</button>
								<button
									onClick={handleSave}
									disabled={isSaving}
									className="py-2 px-5 rounded-lg bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-sm transition-colors disabled:opacity-50 flex items-center justify-center"
								>
									{isSaving ? (
										<IconLoader className="animate-spin h-5 w-5" />
									) : (
										"Save Changes"
									)}
								</button>
							</>
						) : (
							!block.isRecurring && (
								<button
									onClick={() => setIsEditing(true)}
									className="py-2 px-5 rounded-lg bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-sm font-semibold flex items-center gap-2"
								>
									<IconPencil size={16} /> Edit
								</button>
							)
						)}
					</div>
				</div>
			</motion.div>
		</motion.div>
	)
}

export default EntryDetailsModal
