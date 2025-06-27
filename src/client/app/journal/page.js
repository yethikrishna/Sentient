"use client"

import React, { useState, useEffect, useCallback, useRef } from "react"
import Sidebar from "@components/Sidebar"
import {
	IconMenu2,
	IconLoader,
	IconChevronLeft,
	IconChevronRight,
	IconPencil,
	IconTrash,
	IconFileSymlink,
	IconActivity,
	IconChevronDown,
	IconCircleCheck,
	IconAlertCircle,
	IconClock,
	IconX
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { AnimatePresence, motion } from "framer-motion"
import { cn } from "@utils/cn"
import { useRouter } from "next/navigation"

const TaskDetails = ({ task }) => {
	const router = useRouter()
	if (!task) return null

	const statusMap = {
		pending: { icon: IconClock, color: "text-yellow-400" },
		processing: { icon: IconLoader, color: "text-blue-400", animate: true },
		completed: { icon: IconCircleCheck, color: "text-green-400" },
		error: { icon: IconAlertCircle, color: "text-red-400" },
		approval_pending: { icon: IconClock, color: "text-purple-400" },
		cancelled: { icon: IconX, color: "text-gray-500" }
	}

	const StatusIcon = statusMap[task.status]?.icon || IconActivity
	const statusColor = statusMap[task.status]?.color || "text-gray-400"
	const animateStatus = statusMap[task.status]?.animate || false

	return (
		<div
			onClick={() => router.push("/tasks")}
			className="mt-2 text-xs text-gray-400 p-3 bg-neutral-800/60 rounded-md border border-neutral-700/50 cursor-pointer hover:bg-neutral-700/70 transition-colors"
		>
			<div className="flex justify-between items-center mb-2">
				<p className="font-semibold text-gray-200">
					{task.description}
				</p>
				<span
					className={cn(
						"flex items-center gap-1.5 font-medium capitalize",
						statusColor
					)}
				>
					<StatusIcon
						size={14}
						className={cn(animateStatus && "animate-spin")}
					/>
					{task.status.replace("_", " ")}
				</span>
			</div>

			<div className="space-y-2">
				<div>
					<h5 className="font-bold text-gray-300 mb-1">Plan:</h5>
					<ul className="list-decimal list-inside pl-2 space-y-1">
						{task.plan?.map((step, index) => (
							<li key={index} className="text-gray-400">
								<span className="font-semibold text-gray-300">
									{step.tool}:
								</span>{" "}
								{step.description}
							</li>
						))}
					</ul>
				</div>
				{task.progress_updates?.length > 0 && (
					<div>
						<h5 className="font-bold text-gray-300 mb-1">
							Progress:
						</h5>
						<ul className="space-y-1">
							{task.progress_updates.map((update, index) => (
								<li key={index} className="text-gray-400 pl-2">
									- {update.message}
								</li>
							))}
						</ul>
					</div>
				)}
				{(task.result || task.error) && (
					<div>
						<h5 className="font-bold text-gray-300 mb-1">
							Result:
						</h5>
						<p
							className={cn(
								"pl-2 whitespace-pre-wrap",
								task.error ? "text-red-400" : "text-gray-300"
							)}
						>
							{task.result || task.error}
						</p>
					</div>
				)}
			</div>
		</div>
	)
}

const JournalBlock = ({ block, onUpdate, onDelete }) => {
	const [content, setContent] = useState(block.content)
	const [isEditing, setIsEditing] = useState(false)
	const [isExpanded, setIsExpanded] = useState(false)
	const [taskDetails, setTaskDetails] = useState(null)
	const [isLoadingTask, setIsLoadingTask] = useState(false)
	const textareaRef = useRef(null)

	const handleSave = () => {
		if (content.trim() !== block.content) {
			onUpdate(block.block_id, content)
		}
		setIsEditing(false)
	}

	useEffect(() => {
		if (isEditing && textareaRef.current) {
			textareaRef.current.focus()
			textareaRef.current.style.height = "auto"
			textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
		}
	}, [isEditing])

	const handleKeyDown = (e) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault()
			handleSave()
		}
	}

	const fetchTaskDetails = useCallback(async () => {
		if (!block.linked_task_id) return
		setIsLoadingTask(true)
		try {
			const response = await fetch(`/api/tasks/${block.linked_task_id}`)
			if (!response.ok) throw new Error("Failed to fetch task details")
			const data = await response.json()
			setTaskDetails(data)
		} catch (error) {
			toast.error(error.message)
			setTaskDetails(null) // Reset on error
		} finally {
			setIsLoadingTask(false)
		}
	}, [block.linked_task_id])

	useEffect(() => {
		if (isExpanded) {
			fetchTaskDetails()
		}
	}, [isExpanded, fetchTaskDetails])

	// This effect sets up polling for real-time progress updates
	useEffect(() => {
		let intervalId = null
		if (
			isExpanded &&
			taskDetails &&
			["processing", "pending", "approval_pending"].includes(
				taskDetails.status
			)
		) {
			intervalId = setInterval(fetchTaskDetails, 5000) // Poll every 5 seconds
		}
		return () => {
			if (intervalId) {
				clearInterval(intervalId)
			}
		}
	}, [isExpanded, taskDetails, fetchTaskDetails])

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, x: -20 }}
			className="flex items-start gap-3 p-3 rounded-lg hover:bg-neutral-800/50 group"
		>
			<div className="w-4 h-4 mt-1.5 bg-neutral-700 rounded-full flex-shrink-0"></div>
			<div className="flex-1">
				{isEditing ? (
					<textarea
						ref={textareaRef}
						value={content}
						onChange={(e) => setContent(e.target.value)}
						onBlur={handleSave}
						onKeyDown={handleKeyDown}
						className="w-full bg-transparent text-gray-200 resize-none focus:outline-none overflow-hidden"
						rows={1}
					/>
				) : (
					<p
						className="text-gray-200 whitespace-pre-wrap"
						onClick={() => setIsEditing(true)}
					>
						{block.content}
					</p>
				)}
				{block.linked_task_id && (
					<details
						className="mt-2 text-xs"
						onToggle={(e) => setIsExpanded(e.currentTarget.open)}
					>
						<summary className="cursor-pointer select-none flex items-center gap-2 text-blue-400 hover:text-blue-300 font-medium">
							<IconFileSymlink size={16} />
							<span>Plan Generated: {block.task_status}</span>
							<IconChevronDown
								size={16}
								className="transition-transform details-arrow"
							/>
						</summary>
						{isLoadingTask ? (
							<div className="flex justify-center p-4">
								<IconLoader className="animate-spin text-gray-400" />
							</div>
						) : (
							<TaskDetails task={taskDetails} />
						)}
					</details>
				)}
			</div>
			<div className="opacity-0 group-hover:opacity-100 transition-opacity">
				<button
					onClick={() => setIsEditing(true)}
					className="p-1 text-gray-400 hover:text-white"
				>
					<IconPencil size={16} />
				</button>
				<button
					onClick={() => onDelete(block.block_id)}
					className="p-1 text-gray-400 hover:text-red-400"
				>
					<IconTrash size={16} />
				</button>
			</div>
		</motion.div>
	)
}

const JournalPage = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [blocks, setBlocks] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [currentDate, setCurrentDate] = useState(new Date())
	const [newBlockContent, setNewBlockContent] = useState("")
	const newBlockTextareaRef = useRef(null)

	const fetchBlocks = useCallback(async (date) => {
		setIsLoading(true)
		const dateString = date.toISOString().split("T")[0]
		try {
			const response = await fetch(`/api/journal?date=${dateString}`)
			if (!response.ok) throw new Error("Failed to fetch journal entries")
			const data = await response.json()
			setBlocks(data.blocks || [])
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetch("/api/user/profile")
			.then((res) => res.json())
			.then((data) => setUserDetails(data))
		fetchBlocks(currentDate)
	}, [fetchBlocks, currentDate])

	useEffect(() => {
		if (newBlockTextareaRef.current) {
			newBlockTextareaRef.current.style.height = "auto"
			newBlockTextareaRef.current.style.height = `${newBlockTextareaRef.current.scrollHeight}px`
		}
	}, [newBlockContent])

	const handleDateChange = (offset) => {
		setCurrentDate((prevDate) => {
			const newDate = new Date(prevDate)
			newDate.setDate(newDate.getDate() + offset)
			return newDate
		})
	}

	const handleCreateBlock = async (processWithAI = false) => {
		if (!newBlockContent.trim()) return
		const newOrder =
			blocks.length > 0 ? Math.max(...blocks.map((b) => b.order)) + 1 : 0

		try {
			const response = await fetch("/api/journal", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					content: newBlockContent,
					page_date: currentDate.toISOString().split("T")[0],
					order: newOrder,
					processWithAI: processWithAI
				})
			})
			if (!response.ok) throw new Error("Failed to create block")
			const newBlock = await response.json()
			setBlocks((prev) => [...prev, newBlock])
			setNewBlockContent("")
			if (processWithAI) {
				toast.success("Entry sent to AI for processing.")
			}
		} catch (error) {
			toast.error(error.message)
		}
	}

	const handleUpdateBlock = async (blockId, newContent) => {
		setBlocks((prev) =>
			prev.map((b) =>
				b.block_id === blockId ? { ...b, content: newContent } : b
			)
		)
		try {
			const response = await fetch(`/api/journal?blockId=${blockId}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ content: newContent })
			})
			if (!response.ok) throw new Error("Failed to update block")
			// Optionally refresh data
			fetchBlocks(currentDate)
		} catch (error) {
			toast.error(error.message)
			// Revert on error
			fetchBlocks(currentDate)
		}
	}

	const handleDeleteBlock = async (blockId) => {
		const originalBlocks = [...blocks]
		setBlocks((prev) => prev.filter((b) => b.block_id !== blockId))
		try {
			const response = await fetch(`/api/journal?blockId=${blockId}`, {
				method: "DELETE"
			})
			if (!response.ok) throw new Error("Failed to delete block")
		} catch (error) {
			toast.error(error.message)
			setBlocks(originalBlocks)
		}
	}

	const handleKeyDownNewBlock = (e) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault()
			handleCreateBlock(false)
		} else if (e.key === "Enter" && e.shiftKey) {
			e.preventDefault()
			handleCreateBlock(true)
		}
	}

	return (
		<div className="flex h-screen bg-matteblack dark">
			<style jsx global>{`
				details > summary {
					list-style: none;
				}
				details > summary::-webkit-details-marker {
					display: none;
				}
				details[open] .details-arrow {
					transform: rotate(180deg);
				}
			`}</style>
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col overflow-hidden">
				<header className="flex items-center justify-between p-4 bg-matteblack border-b border-neutral-800 shrink-0">
					<button
						onClick={() => setSidebarVisible(true)}
						className="text-white md:hidden"
					>
						<IconMenu2 />
					</button>
					<div className="flex items-center gap-4">
						<h1 className="text-xl font-semibold text-white">
							Journal
						</h1>
						<div className="flex items-center gap-2 bg-neutral-800 rounded-full p-1">
							<button
								onClick={() => handleDateChange(-1)}
								className="p-1.5 text-gray-300 hover:text-white hover:bg-neutral-700 rounded-full"
							>
								<IconChevronLeft size={18} />
							</button>
							<span className="text-sm font-medium text-white w-28 text-center">
								{currentDate.toLocaleDateString(undefined, {
									month: "long",
									day: "numeric",
									year: "numeric"
								})}
							</span>
							<button
								onClick={() => handleDateChange(1)}
								className="p-1.5 text-gray-300 hover:text-white hover:bg-neutral-700 rounded-full"
							>
								<IconChevronRight size={18} />
							</button>
						</div>
					</div>
					<div></div>
				</header>
				<main className="flex-1 flex flex-col overflow-y-auto p-4 sm:p-6 custom-scrollbar">
					<div className="w-full max-w-2xl mx-auto">
						{isLoading ? (
							<div className="flex justify-center py-20">
								<IconLoader className="w-10 h-10 animate-spin text-lightblue" />
							</div>
						) : (
							<AnimatePresence>
								{blocks.map((block) => (
									<JournalBlock
										key={block.block_id}
										block={block}
										onUpdate={handleUpdateBlock}
										onDelete={handleDeleteBlock}
									/>
								))}
							</AnimatePresence>
						)}
						<div className="flex items-start gap-3 p-3">
							<div className="w-4 h-4 mt-1.5 bg-neutral-700 rounded-full flex-shrink-0"></div>
							<textarea
								ref={newBlockTextareaRef}
								value={newBlockContent}
								onChange={(e) =>
									setNewBlockContent(e.target.value)
								}
								onKeyDown={handleKeyDownNewBlock}
								placeholder="Write something... (Shift+Enter to send to AI)"
								className="w-full bg-transparent text-gray-200 resize-none focus:outline-none overflow-hidden"
								rows={1}
							/>
						</div>
					</div>
				</main>
			</div>
		</div>
	)
}

export default JournalPage
