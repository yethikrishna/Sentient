// src/client/components/SQLiteMemoryDisplay.js
"use client"
import React, { useEffect, useState, useCallback } from "react"
import toast from "react-hot-toast"
import {
	IconPencil,
	IconTrash,
	IconPlus,
	IconRefresh,
	IconCalendar,
	IconClock,
	IconListDetails,
	IconDeviceFloppy,
	IconX,
	IconUser,
	IconBriefcase,
	IconUsers,
	IconHeart,
	IconCurrencyDollar,
	IconPeace,
	IconBuilding,
	IconCpu,
	IconHeartbeat,
	IconSchool,
	IconCar,
	IconDeviceGamepad2,
	IconChecklist,
	IconLoader
} from "@tabler/icons-react"
import { cn } from "@utils/cn"

const categoryIcons = {
	PERSONAL: IconUser,
	WORK: IconBriefcase,
	SOCIAL: IconUsers,
	RELATIONSHIP: IconHeart,
	FINANCE: IconCurrencyDollar,
	SPIRITUAL: IconPeace,
	CAREER: IconBuilding,
	TECHNOLOGY: IconCpu,
	HEALTH: IconHeartbeat,
	EDUCATION: IconSchool,
	TRANSPORTATION: IconCar,
	ENTERTAINMENT: IconDeviceGamepad2,
	TASKS: IconChecklist,
	DEFAULT: IconListDetails
}

const categories = [
	"PERSONAL",
	"WORK",
	"SOCIAL",
	"RELATIONSHIP",
	"FINANCE",
	"SPIRITUAL",
	"CAREER",
	"TECHNOLOGY",
	"HEALTH",
	"EDUCATION",
	"TRANSPORTATION",
	"ENTERTAINMENT",
	"TASKS"
]

const SQLiteMemoryDisplay = ({ userDetails, refreshTrigger }) => {
	const [memories, setMemories] = useState([])
	const [selectedCategory, setSelectedCategory] = useState(categories[0])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState(null)
	const [isAddModalOpen, setIsAddModalOpen] = useState(false)
	const [newMemoryText, setNewMemoryText] = useState("")
	const [newMemoryCategory, setNewMemoryCategory] = useState(selectedCategory)
	const [newMemoryRetentionDays, setNewMemoryRetentionDays] = useState(7)
	const [editingMemory, setEditingMemory] = useState(null)
	const [updatedText, setUpdatedText] = useState("")
	const [updatedRetentionDays, setUpdatedRetentionDays] = useState(7)
	const [isSubmitting, setIsSubmitting] = useState(false)

	const fetchMemories = useCallback(async () => {
		if (!selectedCategory) return
		setLoading(true)
		setError(null)
		try {
			const response = await fetch(
				`/api/memory/short-term?category=${selectedCategory.toLowerCase()}`
			)
			const fetchedMemories = await response.json()
			if (!response.ok) {
				throw new Error(
					fetchedMemories.error || "Failed to fetch memories"
				)
			}
			const sortedMemories = (fetchedMemories || []).sort(
				(a, b) => new Date(b.created_at) - new Date(a.created_at)
			)
			setMemories(sortedMemories)
		} catch (error) {
			setError(`Error fetching memories: ${error.message}`)
			setMemories([])
		} finally {
			setLoading(false)
		}
	}, [selectedCategory])

	useEffect(() => {
		fetchMemories()
	}, [fetchMemories, refreshTrigger])

	const openAddModal = () => {
		setNewMemoryCategory(selectedCategory)
		setNewMemoryText("")
		setNewMemoryRetentionDays(7)
		setIsAddModalOpen(true)
	}
	const closeAddModal = () => setIsAddModalOpen(false)

	const openEditModal = (memory) => {
		setEditingMemory(memory)
		setUpdatedText(memory.original_text)
		const expiryDate = new Date(memory.expiry_at)
		const createdDate = new Date(memory.created_at)
		const currentRetention = Math.ceil(
			(expiryDate - createdDate) / (1000 * 60 * 60 * 24)
		)
		setUpdatedRetentionDays(currentRetention > 0 ? currentRetention : 7)
		setIsSubmitting(false)
	}
	const closeEditModal = () => setEditingMemory(null)

	const handleAddMemory = async () => {
		if (!newMemoryText.trim())
			return toast.error("Memory text cannot be empty.")
		const retentionDays = parseInt(newMemoryRetentionDays)
		if (isNaN(retentionDays) || retentionDays < 1 || retentionDays > 90)
			return toast.error("Retention must be between 1-90 days.")

		setIsSubmitting(true)
		try {
			const response = await fetch("/api/memory/short-term/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					text: newMemoryText,
					category: newMemoryCategory.toLowerCase(),
					retention_days: retentionDays
				})
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to add memory")
			toast.success("Memory added successfully")
			closeAddModal()
			fetchMemories()
		} catch (error) {
			toast.error(`Failed to add memory: ${error.message}`)
		} finally {
			setIsSubmitting(false)
		}
	}

	const handleUpdateMemory = async () => {
		if (!editingMemory || !updatedText.trim())
			return toast.error("Memory text cannot be empty.")
		const retentionDays = parseInt(updatedRetentionDays)
		if (isNaN(retentionDays) || retentionDays < 1 || retentionDays > 90)
			return toast.error("Retention must be between 1-90 days.")

		setIsSubmitting(true)
		try {
			const response = await fetch("/api/memory/short-term/update", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					id: editingMemory.id,
					category: editingMemory.category.toLowerCase(),
					text: updatedText,
					retention_days: retentionDays
				})
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to update memory")
			toast.success("Memory updated successfully")
			closeEditModal()
			fetchMemories()
		} catch (error) {
			toast.error(`Failed to update memory: ${error.message}`)
		} finally {
			setIsSubmitting(false)
		}
	}

	const handleDeleteMemory = async (memory) => {
		if (
			!window.confirm(
				`Delete memory: "${memory.original_text.substring(0, 30)}..."?`
			)
		)
			return

		setIsSubmitting(true)
		try {
			const response = await fetch("/api/memory/short-term/delete", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					id: memory.id,
					category: memory.category.toLowerCase()
				})
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to delete memory")
			toast.success("Memory deleted successfully")
			fetchMemories()
		} catch (error) {
			toast.error(`Failed to delete memory: ${error.message}`)
		} finally {
			setIsSubmitting(false)
		}
	}

	// --- JSX ---
	return (
		<div className="w-full h-full flex text-white">
			<div className="w-1/4 h-full flex-shrink-0 border-r border-neutral-700 overflow-y-auto pr-1 custom-scrollbar">
				<div className="p-4 space-y-1.5">
					<h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 px-2">
						Categories
					</h3>
					{categories.map((category) => {
						const CategoryIcon =
							categoryIcons[category] || categoryIcons.DEFAULT
						const isActive = selectedCategory === category
						return (
							<button
								key={category}
								onClick={() => setSelectedCategory(category)}
								className={cn(
									"w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-left transition-colors duration-150",
									isActive
										? "bg-lightblue/20 text-lightblue font-medium"
										: "text-gray-400 hover:bg-neutral-700/50 hover:text-gray-200"
								)}
							>
								<CategoryIcon className="w-5 h-5 flex-shrink-0" />
								<span className="text-sm truncate">
									{category}
								</span>
							</button>
						)
					})}
				</div>
			</div>
			<div className="flex-grow h-full flex flex-col pl-4 pr-2 overflow-hidden">
				<div className="flex justify-between items-center p-4 border-b border-neutral-700 flex-shrink-0">
					<h2 className="text-xl font-semibold text-white capitalize">
						{selectedCategory.toLowerCase()} Memories
					</h2>
					<div className="flex items-center gap-2">
						<button
							onClick={fetchMemories}
							disabled={loading}
							className="p-2 rounded-full text-gray-400 hover:bg-neutral-700 hover:text-white disabled:opacity-50 transition-colors"
							title="Refresh Memories"
						>
							{loading ? (
								<IconLoader className="w-5 h-5 animate-spin" />
							) : (
								<IconRefresh className="w-5 h-5" />
							)}
						</button>
						<button
							onClick={openAddModal}
							className="flex items-center gap-1.5 py-2 px-4 rounded-full bg-lightblue hover:bg-blue-700 text-white text-sm font-medium transition-colors"
							title="Add New Memory"
						>
							<IconPlus className="w-4 h-4" /> Add Memory
						</button>
					</div>
				</div>
				<div className="flex-grow overflow-y-auto py-4 space-y-3 custom-scrollbar">
					{loading ? (
						<div className="text-center text-gray-500 py-10">
							<IconLoader className="w-6 h-6 animate-spin inline mr-2" />
							Loading...
						</div>
					) : error ? (
						<div className="text-center text-red-500 py-10">
							{error}
						</div>
					) : memories.length === 0 ? (
						<div className="text-center text-gray-500 py-10">
							No memories found in this category.
						</div>
					) : (
						memories.map((memory) => (
							<div
								key={memory.id}
								className="bg-neutral-800/70 p-4 rounded-lg border border-neutral-700 shadow-sm hover:border-neutral-600 transition-colors"
							>
								<p className="text-gray-200 text-sm mb-3 leading-relaxed">
									{memory.original_text}
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
											memory.expiry_at
										).toLocaleDateString()}
									</span>
									<div className="flex gap-1">
										<button
											onClick={() =>
												openEditModal(memory)
											}
											className="p-1 text-yellow-400 hover:text-yellow-300 rounded hover:bg-neutral-700 transition-colors"
											title="Edit Memory"
										>
											<IconPencil className="w-4 h-4" />
										</button>
										<button
											onClick={() =>
												handleDeleteMemory(memory)
											}
											className="p-1 text-red-400 hover:text-red-300 rounded hover:bg-neutral-700 transition-colors"
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
			</div>
			{isAddModalOpen && (
				<div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4">
					<div className="bg-neutral-800 p-6 rounded-lg shadow-xl w-full max-w-lg mx-auto border border-neutral-700">
						<div className="flex justify-between items-center mb-5">
							<h3 className="text-lg font-semibold text-white">
								Add New Memory
							</h3>
							<button
								onClick={closeAddModal}
								className="text-gray-400 hover:text-white"
							>
								<IconX size={20} />
							</button>
						</div>
						<div className="space-y-4">
							<div>
								<label className="block text-gray-400 text-sm font-medium mb-1">
									Memory Text
								</label>
								<textarea
									value={newMemoryText}
									onChange={(e) =>
										setNewMemoryText(e.target.value)
									}
									placeholder="Enter the memory details..."
									rows={4}
									className="w-full p-2.5 bg-neutral-700 border border-neutral-600 rounded text-white focus:outline-none focus:border-lightblue text-sm resize-none"
								/>
							</div>
							<div className="grid grid-cols-2 gap-4">
								<div>
									<label className="block text-gray-400 text-sm font-medium mb-1">
										Category
									</label>
									<select
										value={newMemoryCategory}
										onChange={(e) =>
											setNewMemoryCategory(e.target.value)
										}
										className="w-full p-2.5 bg-neutral-700 border border-neutral-600 rounded text-white focus:outline-none focus:border-lightblue appearance-none text-sm"
									>
										{categories.map((cat) => (
											<option key={cat} value={cat}>
												{cat}
											</option>
										))}
									</select>
								</div>
								<div>
									<label className="block text-gray-400 text-sm font-medium mb-1">
										Retention (Days)
									</label>
									<input
										type="number"
										min="1"
										max="90"
										value={newMemoryRetentionDays}
										onChange={(e) =>
											setNewMemoryRetentionDays(
												e.target.value
											)
										}
										className="w-full p-2.5 bg-neutral-700 border border-neutral-600 rounded text-white focus:outline-none focus:border-lightblue text-sm"
									/>
								</div>
							</div>
						</div>
						<div className="flex justify-end gap-3 mt-6">
							<button
								onClick={closeAddModal}
								className="py-2 px-4 rounded bg-neutral-600 hover:bg-neutral-500 text-white text-sm font-medium transition-colors"
							>
								Cancel
							</button>
							<button
								onClick={handleAddMemory}
								disabled={isSubmitting}
								className="py-2 px-5 rounded bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
							>
								{isSubmitting ? (
									<IconLoader className="w-4 h-4 animate-spin" />
								) : (
									<IconDeviceFloppy className="w-4 h-4" />
								)}
								{isSubmitting ? "Saving..." : "Save Memory"}
							</button>
						</div>
					</div>
				</div>
			)}
			{editingMemory && (
				<div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4">
					<div className="bg-neutral-800 p-6 rounded-lg shadow-xl w-full max-w-lg mx-auto border border-neutral-700">
						<div className="flex justify-between items-center mb-5">
							<h3 className="text-lg font-semibold text-white">
								Edit Memory (Category: {editingMemory.category})
							</h3>
							<button
								onClick={closeEditModal}
								className="text-gray-400 hover:text-white"
							>
								<IconX size={20} />
							</button>
						</div>
						<div className="space-y-4">
							<div>
								<label className="block text-gray-400 text-sm font-medium mb-1">
									Memory Text
								</label>
								<textarea
									value={updatedText}
									onChange={(e) =>
										setUpdatedText(e.target.value)
									}
									rows={4}
									className="w-full p-2.5 bg-neutral-700 border border-neutral-600 rounded text-white focus:outline-none focus:border-lightblue text-sm resize-none"
								/>
							</div>
							<div>
								<label className="block text-gray-400 text-sm font-medium mb-1">
									New Retention (Days from now)
								</label>
								<input
									type="number"
									min="1"
									max="90"
									value={updatedRetentionDays}
									onChange={(e) =>
										setUpdatedRetentionDays(e.target.value)
									}
									className="w-full p-2.5 bg-neutral-700 border border-neutral-600 rounded text-white focus:outline-none focus:border-lightblue text-sm"
								/>
							</div>
						</div>
						<div className="flex justify-end gap-3 mt-6">
							<button
								onClick={closeEditModal}
								className="py-2 px-4 rounded bg-neutral-600 hover:bg-neutral-500 text-white text-sm font-medium transition-colors"
							>
								Cancel
							</button>
							<button
								onClick={handleUpdateMemory}
								disabled={isSubmitting}
								className="py-2 px-5 rounded bg-green-600 hover:bg-green-500 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
							>
								{isSubmitting ? (
									<IconLoader className="w-4 h-4 animate-spin" />
								) : (
									<IconDeviceFloppy className="w-4 h-4" />
								)}
								{isSubmitting ? "Saving..." : "Save Changes"}
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	)
}

export default SQLiteMemoryDisplay
