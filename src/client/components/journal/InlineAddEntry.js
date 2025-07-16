"use client"

import React, { useState, useEffect, useRef } from "react"
import { usePostHog } from "posthog-js/react"
import toast from "react-hot-toast"
import { format } from "date-fns"

const InlineAddEntry = ({ day, onSave, onCancel }) => {
	const [content, setContent] = useState("")
	const posthog = usePostHog()
	const [isSubmitting, setIsSubmitting] = useState(false) // eslint-disable-line
	const textareaRef = useRef(null)

	useEffect(() => {
		textareaRef.current?.focus()
	}, [])

	const handleSave = async () => {
		if (!content.trim()) return
		setIsSubmitting(true)
		try {
			// Always create a journal entry now
			const response = await fetch("/api/journal", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					content: content,
					page_date: format(day, "yyyy-MM-dd"),
					order: 0,
					processWithAI: true // Always process as a potential task
				})
			})
			if (!response.ok) throw new Error("Failed to create entry")
			posthog?.capture("journal_entry_created")
			toast.success("Entry saved and sent for processing.")
			onSave()
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsSubmitting(false)
		}
	}

	return (
		<div className="flex flex-col">
			<textarea
				ref={textareaRef}
				value={content}
				onChange={(e) => setContent(e.target.value)}
				placeholder="Type anything or describe a task to schedule..."
				className="w-full bg-transparent p-2 rounded-md resize-none focus:outline-none placeholder:text-neutral-500 text-sm"
				rows={3}
			></textarea>
			<div className="flex justify-end items-center mt-2">
				<div className="flex gap-2"></div>
				<div className="flex justify-end gap-2">
					<button
						onClick={onCancel}
						className="px-3 py-1 text-xs rounded-md hover:bg-[var(--color-primary-surface-elevated)]"
					>
						Cancel
					</button>
					<button
						onClick={handleSave}
						disabled={isSubmitting || !content.trim()}
						className="px-4 py-1 text-xs font-semibold bg-[var(--color-accent-blue)] text-white rounded-md disabled:opacity-50"
					>
						{isSubmitting ? "Saving..." : "Save"}
					</button>
				</div>
			</div>
		</div>
	)
}

export default InlineAddEntry
