// src/client/components/ShortTermMemoryDisplay.js
"use client"
import React, { useEffect, useState, useCallback } from "react"
import toast from "react-hot-toast"
import {
	IconUser,
	IconClock,
	IconEdit,
	IconTrash,
	IconCalendar,
	IconBriefcase,
	IconUsers,
	IconHeart,
	IconCurrencyDollar,
	IconHeartbeat,
	IconAdjustments,
	IconListDetails,
	IconLoader
} from "@tabler/icons-react"
import { cn } from "@utils/cn"

const categoryIcons = {
	Personal: IconUser,
	Professional: IconBriefcase,
	Social: IconUsers,
	Financial: IconCurrencyDollar,
	Health: IconHeartbeat,
	Preferences: IconAdjustments,
	Events: IconCalendar,
	General: IconListDetails,
	DEFAULT: IconListDetails
}

const categories = [
	"Personal",
	"Professional",
	"Social",
	"Financial",
	"Health",
	"Preferences",
	"Events",
	"General"
]

const ShortTermMemoryDisplay = ({ userDetails, refreshTrigger }) => {
	const [memories, setMemories] = useState([])
	const [selectedCategory, setSelectedCategory] = useState(categories[0])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)
	const [editingMemory, setEditingMemory] = useState(null)
	const [updatedText, setUpdatedText] = useState("")
	const [updatedRetention, setUpdatedRetention] = useState(7) // Default 7 days

	const fetchMemories = useCallback(async () => {
		setLoading(true)
		setError(null)
		try {
			const response = await fetch(
				`/api/memory/short-term?category=${selectedCategory.toLowerCase()}`
			)
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to fetch memories")
			}
			// The API returns an object { memories: [...] }
			const sortedMemories = (data.memories || []).sort(
				(a, b) => new Date(b.created_at) - new Date(a.created_at)
			)
			setMemories(sortedMemories)
		} catch (error) {
			setError(`Error fetching memories: ${error.message}`)
			setMemories([])
		} finally {
			setLoading(false)
		}
	}, [selectedCategory, refreshTrigger])

	useEffect(() => {
		fetchMemories()
	}, [fetchMemories])

	const openEditModal = (memory) => {
		setEditingMemory(memory)
		setUpdatedText(memory.content)
		const expiryDate = new Date(memory.expire_at)
		const createdDate = new Date(memory.created_at)
		const currentRetention = Math.ceil(
			(expiryDate - createdDate) / (1000 * 60 * 60 * 24)
		)
		setUpdatedRetention(currentRetention > 0 ? currentRetention : 1) // Ensure retention is at least 1
	}

	const closeEditModal = () => {
		setEditingMemory(null)
		setUpdatedText("")
		setUpdatedRetention(7)
	}

	const handleUpdateMemory = async (e) => {
		e.preventDefault()
		if (!editingMemory) return

		setLoading(true)
		try {
			const response = await fetch("/api/memory/short-term", {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					memory_id: editingMemory._id,
					content: updatedText,
					retention_days: updatedRetention
				})
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to update memory")
			}
			toast.success("Memory updated successfully!")
			fetchMemories()
			closeEditModal()
		} catch (error) {
			toast.error(`Error updating memory: ${error.message}`)
		} finally {
			setLoading(false)
		}
	}

	const handleDeleteMemory = async (memory) => {
		if (
			!window.confirm(
				`Delete memory: "${memory.content.substring(0, 30)}..."?`
			)
		)
			return

		setLoading(true)
		try {
			const response = await fetch("/api/memory/short-term", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					memory_id: memory._id
				})
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to delete memory")
			}
			toast.success("Memory deleted successfully!")
			fetchMemories()
		} catch (error) {
			toast.error(`Error deleting memory: ${error.message}`)
		} finally {
			setLoading(false)
		}
	}

	const CategoryIcon =
		categoryIcons[selectedCategory] || categoryIcons.DEFAULT

	return (
		<div className="w-full max-w-4xl mx-auto p-4 bg-neutral-900 rounded-lg shadow-lg border border-neutral-700">
			<h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
				<CategoryIcon className="w-7 h-7 text-blue-400" />
				Short-Term Memory
			</h2>

			<div className="mb-6">
				<label
					htmlFor="category-select"
					className="block text-sm font-medium text-gray-300 mb-2"
				>
					Select Category:
				</label>
				<select
					id="category-select"
					value={selectedCategory}
					onChange={(e) => setSelectedCategory(e.target.value)}
					className="w-full p-2 bg-neutral-800 border border-neutral-700 rounded-md text-white focus:ring-blue-500 focus:border-blue-500"
				>
					{categories.map((cat) => (
						<option key={cat} value={cat}>
							{cat}
						</option>
					))}
				</select>
			</div>

			{error && <p className="text-red-500 text-sm mb-4">{error}</p>}

			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{loading ? (
					<div className="col-span-full flex justify-center items-center py-8">
						<IconLoader className="w-8 h-8 animate-spin text-blue-400" />
						<span className="ml-2 text-gray-400">
							Loading memories...
						</span>
					</div>
				) : memories.length === 0 ? (
					<div className="col-span-full text-center py-8 text-gray-400">
						No memories found for this category.
					</div>
				) : (
					memories.map((memory) => (
						<div
							key={memory._id}
							className="bg-neutral-800/70 p-4 rounded-lg border border-neutral-700 shadow-sm hover:border-neutral-600 transition-colors"
						>
							<p className="text-gray-200 text-sm mb-3 leading-relaxed">
								{memory.content}
							</p>
							<div className="flex justify-between items-center text-xs text-gray-500 border-t border-neutral-700 pt-2 mt-2">
								<span className="flex items-center gap-1">
									<IconCalendar className="w-3.5 h-3.5" />
									Created:{" "}
									{new Date(
										memory.created_at
									).toLocaleDateString()}
								</span>
								<span className="flex items-center gap-1">
									<IconClock className="w-3.5 h-3.5" />
									Expires:{" "}
									{new Date(
										memory.expire_at
									).toLocaleDateString()}
								</span>
								<div className="flex gap-1">
									<button
										onClick={() => openEditModal(memory)}
										className="p-1 rounded-full hover:bg-neutral-700 text-blue-400 transition-colors"
										title="Edit Memory"
									>
										<IconEdit className="w-4 h-4" />
									</button>
									<button
										onClick={() =>
											handleDeleteMemory(memory)
										}
										className="p-1 rounded-full hover:bg-neutral-700 text-red-400 transition-colors"
										title="Delete Memory"
									>
										<IconTrash className="w-4 h-4" />
									</button>
								</div>
							</div>
						</div>
					))
				)}
			</div>

			{editingMemory && (
				<div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-50">
					<div className="bg-neutral-800 p-6 rounded-lg shadow-xl w-full max-w-md border border-neutral-700">
						<h3 className="text-xl font-bold text-white mb-4">
							Edit Memory
						</h3>
						<form onSubmit={handleUpdateMemory}>
							<div className="mb-4">
								<label
									htmlFor="memory-text"
									className="block text-sm font-medium text-gray-300 mb-2"
								>
									Memory Content:
								</label>
								<textarea
									id="memory-text"
									value={updatedText}
									onChange={(e) =>
										setUpdatedText(e.target.value)
									}
									rows="4"
									className="w-full p-2 bg-neutral-700 border border-neutral-600 rounded-md text-white focus:ring-blue-500 focus:border-blue-500"
									required
								></textarea>
							</div>
							<div className="mb-4">
								<label
									htmlFor="retention-days"
									className="block text-sm font-medium text-gray-300 mb-2"
								>
									Retention (days):
								</label>
								<input
									type="number"
									id="retention-days"
									value={updatedRetention}
									onChange={(e) =>
										setUpdatedRetention(
											Math.max(
												1,
												parseInt(e.target.value) || 1
											)
										)
									}
									min="1"
									className="w-full p-2 bg-neutral-700 border border-neutral-600 rounded-md text-white focus:ring-blue-500 focus:border-blue-500"
									required
								/>
							</div>
							<div className="flex justify-end gap-3">
								<button
									type="button"
									onClick={closeEditModal}
									className="px-4 py-2 bg-neutral-600 text-white rounded-md hover:bg-neutral-700 transition-colors"
								>
									Cancel
								</button>
								<button
									type="submit"
									className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center"
									disabled={loading}
								>
									{loading && (
										<IconLoader className="w-4 h-4 mr-2 animate-spin" />
									)}
									Update Memory
								</button>
							</div>
						</form>
					</div>
				</div>
			)}
		</div>
	)
}

export default ShortTermMemoryDisplay
