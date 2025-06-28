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
	IconX,
	IconSparkles
} from "@tabler/icons-react"
import toast from "react-hot-toast"
import { AnimatePresence, motion } from "framer-motion"
import { cn } from "@utils/cn"
import { useRouter } from "next/navigation"
import { useSmoothScroll } from "@hooks/useSmoothScroll"

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
		<motion.div
			onClick={() => router.push("/tasks")}
			className="mt-2 text-xs text-gray-400 p-3 bg-[var(--color-primary-surface)] rounded-[var(--radius-base)] border border-[#3a3a3a] cursor-pointer hover:bg-[var(--color-primary-surface-elevated)] transition-all duration-200 hover:transform hover:scale-[1.02] hover:shadow-lg group"
			whileHover={{
				rotateX: 2,
				transition: { duration: 0.2 }
			}}
		>
			<div className="flex justify-between items-center mb-2 group-hover:text-[var(--color-text-primary)] transition-colors duration-200">
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
								task.error
									? "text-[var(--color-accent-red)]"
									: "text-gray-300"
							)}
						>
							{task.result || task.error}
						</p>
					</div>
				)}
			</div>
		</motion.div>
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
		<motion.article
			layout
			initial={{ opacity: 0, y: 20, scale: 0.95 }}
			animate={{
				opacity: 1,
				y: 0,
				scale: 1,
				transition: {
					type: "spring",
					stiffness: 300,
					damping: 25
				}
			}}
			exit={{
				opacity: 0,
				x: -20,
				scale: 0.95,
				transition: { duration: 0.2 }
			}}
			whileHover={{
				scale: 1.01,
				transition: { duration: 0.2 }
			}}
			className="flex items-start gap-3 p-4 rounded-[var(--radius-lg)] hover:bg-[var(--color-primary-surface)]/50 group transition-all duration-200 hover:shadow-sm border border-transparent hover:border-[#3a3a3a]/30"
		>
			<motion.div
				className="w-3 h-3 mt-2 bg-[var(--color-accent-blue)] rounded-full flex-shrink-0"
				whileHover={{ scale: 1.2 }}
				transition={{ type: "spring", stiffness: 400 }}
			></motion.div>
			<div className="flex-1">
				{isEditing ? (
					<textarea
						ref={textareaRef}
						value={content}
						onChange={(e) => setContent(e.target.value)}
						onBlur={handleSave}
						onKeyDown={handleKeyDown}
						className="w-full bg-transparent text-[var(--color-text-primary)] resize-none focus:outline-none overflow-hidden border-none focus:ring-2 focus:ring-[var(--color-accent-blue)]/30 rounded-[var(--radius-sm)] p-2 -m-2"
						rows={1}
					/>
				) : (
					<motion.p
						className="text-[var(--color-text-primary)] whitespace-pre-wrap cursor-text hover:bg-[var(--color-primary-surface)]/30 rounded-[var(--radius-sm)] p-2 -m-2 transition-colors duration-150"
						onClick={() => setIsEditing(true)}
						whileHover={{ x: 2 }}
						transition={{ duration: 0.15 }}
					>
						{block.content}
					</motion.p>
				)}
				{block.linked_task_id && (
					<motion.details
						className="mt-3 text-xs"
						onToggle={(e) => setIsExpanded(e.currentTarget.open)}
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						transition={{ delay: 0.2 }}
					>
						<motion.summary
							className="cursor-pointer select-none flex items-center gap-2 text-[var(--color-accent-blue)] hover:text-[var(--color-accent-blue)]/80 font-medium p-2 rounded-[var(--radius-sm)] hover:bg-[var(--color-primary-surface)]/30 transition-colors duration-150"
							whileHover={{ x: 4 }}
							transition={{ duration: 0.15 }}
						>
							<motion.div
								whileHover={{ rotate: 15 }}
								transition={{ duration: 0.2 }}
							>
								<IconSparkles size={16} />
							</motion.div>
							<span>Plan Generated: {block.task_status}</span>
							<motion.div
								animate={{ rotate: isExpanded ? 180 : 0 }}
								transition={{ duration: 0.2 }}
							>
								<IconChevronDown size={16} />
							</motion.div>
						</motion.summary>
						{isLoadingTask ? (
							<motion.div
								className="flex justify-center p-4"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
							>
								<motion.div
									animate={{ rotate: 360 }}
									transition={{
										duration: 1,
										repeat: Infinity,
										ease: "linear"
									}}
								>
									<IconLoader className="text-[var(--color-accent-blue)]" />
								</motion.div>
							</motion.div>
						) : (
							<motion.div
								initial={{ opacity: 0, y: -10 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.3 }}
							>
								<TaskDetails task={taskDetails} />
							</motion.div>
						)}
					</motion.details>
				)}
			</div>
			<motion.div
				className="opacity-0 group-hover:opacity-100 transition-all duration-200 flex gap-1"
				initial={{ x: 10, opacity: 0 }}
				animate={{ x: 0 }}
			>
				<motion.button
					onClick={() => setIsEditing(true)}
					className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-primary-surface)] rounded-[var(--radius-sm)] transition-colors duration-150"
					whileHover={{ scale: 1.1 }}
					whileTap={{ scale: 0.95 }}
				>
					<IconPencil size={16} />
				</motion.button>
				<motion.button
					onClick={() => onDelete(block.block_id)}
					className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-accent-red)] hover:bg-[var(--color-accent-red)]/10 rounded-[var(--radius-sm)] transition-colors duration-150"
					whileHover={{ scale: 1.1 }}
					whileTap={{ scale: 0.95 }}
				>
					<IconTrash size={16} />
				</motion.button>
			</motion.div>
		</motion.article>
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
	const scrollRef = useRef(null)

	useSmoothScroll(scrollRef)

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
		<div className="flex h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)]">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-1 flex flex-col overflow-hidden">
				<motion.header
					className="flex items-center justify-between p-6 bg-[var(--color-primary-background)] border-b border-[var(--color-primary-surface)] shrink-0"
					initial={{ opacity: 0, y: -20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.3 }}
				>
					<motion.button
						onClick={() => setSidebarVisible(true)}
						className="text-[var(--color-text-primary)] md:hidden p-2 hover:bg-[var(--color-primary-surface)] rounded-[var(--radius-base)] transition-colors duration-150"
						whileHover={{ scale: 1.05 }}
						whileTap={{ scale: 0.95 }}
					>
						<IconMenu2 />
					</motion.button>
					<div className="flex items-center gap-6">
						<motion.h1
							className="text-2xl font-semibold text-[var(--color-text-primary)]"
							initial={{ opacity: 0, x: -20 }}
							animate={{ opacity: 1, x: 0 }}
							transition={{ delay: 0.1 }}
						>
							Journal
						</motion.h1>
						<motion.div
							className="flex items-center gap-1 bg-[var(--color-primary-surface)] rounded-full p-1 border border-[var(--color-primary-surface-elevated)]"
							initial={{ opacity: 0, scale: 0.9 }}
							animate={{ opacity: 1, scale: 1 }}
							transition={{ delay: 0.2 }}
						>
							<motion.button
								onClick={() => handleDateChange(-1)}
								className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-primary-surface-elevated)] rounded-full transition-colors duration-150"
								whileHover={{ scale: 1.1 }}
								whileTap={{ scale: 0.9 }}
							>
								<IconChevronLeft size={18} />
							</motion.button>
							<motion.span
								className="text-sm font-medium text-[var(--color-text-primary)] w-32 text-center"
								key={currentDate.toDateString()}
								initial={{ opacity: 0, y: 10 }}
								animate={{ opacity: 1, y: 0 }}
								transition={{ duration: 0.2 }}
							>
								{currentDate.toLocaleDateString(undefined, {
									month: "long",
									day: "numeric",
									year: "numeric"
								})}
							</motion.span>
							<motion.button
								onClick={() => handleDateChange(1)}
								className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-primary-surface-elevated)] rounded-full transition-colors duration-150"
								whileHover={{ scale: 1.1 }}
								whileTap={{ scale: 0.9 }}
							>
								<IconChevronRight size={18} />
							</motion.button>
						</motion.div>
					</div>
					<div></div>
				</motion.header>
				<main
					ref={scrollRef}
					className="flex-1 flex flex-col overflow-y-auto p-6 no-scrollbar"
				>
					<motion.div
						className="w-full max-w-4xl mx-auto"
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						transition={{ delay: 0.3, duration: 0.4 }}
					>
						{isLoading ? (
							<motion.div
								className="flex justify-center py-20"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
							>
								<motion.div
									animate={{ rotate: 360 }}
									transition={{
										duration: 1,
										repeat: Infinity,
										ease: "linear"
									}}
								>
									<IconLoader className="w-10 h-10 text-[var(--color-accent-blue)]" />
								</motion.div>
							</motion.div>
						) : (
							<AnimatePresence mode="popLayout">
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
						<motion.div
							className="flex items-start gap-3 p-4 rounded-[var(--radius-lg)] hover:bg-[var(--color-primary-surface)]/30 transition-colors duration-200 border border-transparent hover:border-[#3a3a3a]/30"
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ delay: 0.4 }}
						>
							<motion.div
								className="w-3 h-3 mt-2 bg-[var(--color-text-muted)] rounded-full flex-shrink-0"
								whileHover={{
									scale: 1.2,
									backgroundColor: "var(--color-accent-blue)"
								}}
								transition={{ duration: 0.2 }}
							></motion.div>
							<textarea
								ref={newBlockTextareaRef}
								value={newBlockContent}
								onChange={(e) =>
									setNewBlockContent(e.target.value)
								}
								onKeyDown={handleKeyDownNewBlock}
								placeholder="Write something... (Enter to save, Shift+Enter to send to AI)"
								className="w-full bg-transparent text-[var(--color-text-primary)] resize-none focus:outline-none overflow-hidden placeholder-[var(--color-text-muted)] border-none focus:ring-2 focus:ring-[var(--color-accent-blue)]/30 rounded-[var(--radius-sm)] p-2 -m-2"
								rows={1}
							/>
						</motion.div>
					</motion.div>
				</main>
			</div>
		</div>
	)
}

export default JournalPage
