"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import toast from "react-hot-toast"
import { IconLoader } from "@tabler/icons-react"

const DeleteConfirmationModal = ({ block, onClose, onDataChange }) => {
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleConfirmDelete = async () => {
		setIsSubmitting(true)
		try {
			const response = await fetch(
				`/api/organizer?blockId=${block.block_id}`,
				{ method: "DELETE" }
			)
			if (!response.ok) throw new Error("Failed to delete block.")
			toast.success("Entry deleted.")
			onDataChange()
			onClose()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-md border border-[var(--color-primary-surface-elevated)]"
			>
				<h2 className="text-xl font-bold mb-2">Delete Entry?</h2>
				<p className="text-[var(--color-text-muted)] mb-6">
					Are you sure you want to permanently delete this organizer
					entry? This action cannot be undone.
				</p>
				<div className="flex justify-end gap-3">
					<button
						onClick={onClose}
						disabled={isSubmitting}
						className="px-4 py-2 text-sm rounded-lg hover:bg-[var(--color-primary-surface-elevated)]"
					>
						Cancel
					</button>
					<button
						onClick={handleConfirmDelete}
						disabled={isSubmitting}
						className="px-6 py-2 text-sm font-medium bg-[var(--color-accent-red)] hover:bg-[var(--color-accent-red-hover)] text-white rounded-xl disabled:opacity-50 shadow-lg shadow-red-500/20 transition-colors"
					>
						{isSubmitting ? "Deleting..." : "Delete"}
					</button>
				</div>
			</motion.div>
		</motion.div>
	)
}

export default DeleteConfirmationModal
