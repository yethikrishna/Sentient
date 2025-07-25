"use client"

import React, { useState } from "react"
import toast from "react-hot-toast"
import { motion } from "framer-motion"
import { IconX, IconLoader } from "@tabler/icons-react"

const CreateProjectModal = ({ onClose, onProjectCreated }) => {
	const [name, setName] = useState("")
	const [description, setDescription] = useState("")
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleSubmit = async (e) => {
		e.preventDefault()
		if (!name.trim()) {
			toast.error("Project name is required.")
			return
		}
		setIsSubmitting(true)
		try {
			const res = await fetch("/api/projects", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ name, description })
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.detail || "Failed to create project")
			}
			toast.success("Project created successfully!")
			onProjectCreated()
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
			onClick={onClose}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
		>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-neutral-900 p-6 rounded-2xl shadow-xl w-full max-w-md border border-neutral-700"
			>
				<div className="flex justify-between items-center mb-6">
					<h2 className="text-xl font-semibold text-white">
						Create New Project
					</h2>
					<button
						onClick={onClose}
						className="p-1 rounded-full hover:bg-neutral-700"
					>
						<IconX size={20} />
					</button>
				</div>
				<form onSubmit={handleSubmit} className="space-y-4">
					<div>
						<label
							htmlFor="projectName"
							className="block text-sm font-medium text-neutral-300 mb-2"
						>
							Project Name
						</label>
						<input
							id="projectName"
							type="text"
							value={name}
							onChange={(e) => setName(e.target.value)}
							placeholder="e.g., Q4 Marketing Campaign"
							className="w-full p-3 bg-neutral-800 border border-neutral-700 rounded-lg focus:border-blue-500"
							required
						/>
					</div>
					<div>
						<label
							htmlFor="projectDescription"
							className="block text-sm font-medium text-neutral-300 mb-2"
						>
							Description (Optional)
						</label>
						<textarea
							id="projectDescription"
							value={description}
							onChange={(e) => setDescription(e.target.value)}
							placeholder="What is this project about?"
							rows={3}
							className="w-full p-3 bg-neutral-800 border border-neutral-700 rounded-lg resize-none focus:border-blue-500"
						/>
					</div>
					<div className="flex justify-end gap-4 pt-4">
						<button
							type="button"
							onClick={onClose}
							className="py-2.5 px-5 rounded-lg bg-neutral-700 hover:bg-neutral-600 text-sm font-medium transition-colors"
						>
							Cancel
						</button>
						<button
							type="submit"
							disabled={isSubmitting}
							className="py-2.5 px-5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium flex items-center gap-2 disabled:opacity-50 transition-colors"
						>
							{isSubmitting && (
								<IconLoader
									size={16}
									className="animate-spin"
								/>
							)}
							{isSubmitting ? "Creating..." : "Create Project"}
						</button>
					</div>
				</form>
			</motion.div>
		</motion.div>
	)
}

export default CreateProjectModal
