"use client"

import React, { useState, useEffect, useMemo, useRef, useCallback } from "react"
import toast from "react-hot-toast"
import {
	IconLoader,
	IconBrain,
	IconTag,
	IconClock,
	IconFileText,
	IconX,
	IconLayoutGrid,
	IconShare3,
	IconInfoCircle,
	IconSparkles,
	IconHeart,
	IconPlus,
	IconPencil,
	IconTrash,
	IconDeviceFloppy
} from "@tabler/icons-react"
import { motion, AnimatePresence } from "framer-motion"
import { formatDistanceToNow, parseISO } from "date-fns"
import { cn } from "@utils/cn"
import dynamic from "next/dynamic"
import { usePlan } from "@hooks/usePlan"
import InteractiveNetworkBackground from "@components/ui/InteractiveNetworkBackground"
import ModalDialog from "@components/ModalDialog"

const proPlanFeatures = [
	{ name: "Text Chat", limit: "100 messages per day" },
	{ name: "Voice Chat", limit: "10 minutes per day" },
	{ name: "One-Time Tasks", limit: "20 async tasks per day" },
	{ name: "Recurring Tasks", limit: "10 active recurring workflows" },
	{ name: "Triggered Tasks", limit: "10 triggered workflows" },
	{
		name: "Parallel Agents",
		limit: "5 complex tasks per day with 50 sub agents"
	},
	{ name: "File Uploads", limit: "20 files per day" },
	{ name: "Memories", limit: "Unlimited memories" },
	{
		name: "Other Integrations",
		limit: "Notion, GitHub, Slack, Discord, Trello"
	}
]

const UpgradeToProModal = ({ isOpen, onClose }) => {
	if (!isOpen) return null

	const handleUpgrade = () => {
		const dashboardUrl = process.env.NEXT_PUBLIC_LANDING_PAGE_URL
		if (dashboardUrl) {
			window.location.href = `${dashboardUrl}/dashboard`
		}
		onClose()
	}

	return (
		<AnimatePresence>
			{isOpen && (
				<motion.div
					initial={{ opacity: 0 }}
					animate={{ opacity: 1 }}
					exit={{ opacity: 0 }}
					className="fixed inset-0 bg-black/70 backdrop-blur-md z-[100] flex items-center justify-center p-4"
					onClick={onClose}
				>
					<motion.div
						initial={{ scale: 0.95, y: 20 }}
						animate={{ scale: 1, y: 0 }}
						exit={{ scale: 0.95, y: -20 }}
						transition={{ duration: 0.2, ease: "easeInOut" }}
						onClick={(e) => e.stopPropagation()}
						className="relative bg-neutral-900/90 backdrop-blur-xl p-6 rounded-2xl shadow-2xl w-full max-w-lg border border-neutral-700 flex flex-col"
					>
						<header className="text-center mb-4">
							<h2 className="text-2xl font-bold text-white flex items-center justify-center gap-2">
								<IconSparkles className="text-brand-orange" />
								Upgrade to Pro
							</h2>
							<p className="text-neutral-400 mt-2">
								Unlock unlimited memories and other powerful
								features.
							</p>
						</header>
						<main className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 my-4">
							{proPlanFeatures.map((feature) => (
								<div
									key={feature.name}
									className="flex items-start gap-2.5"
								>
									<IconCheck
										size={18}
										className="text-green-400 flex-shrink-0 mt-0.5"
									/>
									<div>
										<p className="text-white text-sm font-medium">
											{feature.name}
										</p>
										<p className="text-neutral-400 text-xs">
											{feature.limit}
										</p>
									</div>
								</div>
							))}
						</main>
						<footer className="mt-4 flex flex-col gap-2">
							<button
								onClick={handleUpgrade}
								className="w-full py-2.5 px-5 rounded-lg bg-brand-orange hover:bg-brand-orange/90 text-brand-black font-semibold transition-colors"
							>
								Upgrade to Pro - $9/month
							</button>
							<button
								onClick={onClose}
								className="w-full py-2 px-5 rounded-lg hover:bg-neutral-800 text-sm font-medium text-neutral-400"
							>
								Not now
							</button>
						</footer>
					</motion.div>
				</motion.div>
			)}
		</AnimatePresence>
	)
}

const InfoPanel = ({ onClose, title, children }) => (
	<motion.div
		initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
		animate={{ opacity: 1, backdropFilter: "blur(12px)" }}
		exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
		className="fixed inset-0 bg-black/70 z-[60] flex p-4 md:p-6"
		onClick={onClose}
	>
		<motion.div
			initial={{ opacity: 0, y: 20 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, y: 20 }}
			transition={{ duration: 0.2, ease: "easeInOut" }}
			onClick={(e) => e.stopPropagation()}
			className="relative bg-neutral-900/80 backdrop-blur-2xl p-6 rounded-2xl shadow-2xl w-full h-full border border-neutral-700 flex flex-col"
		>
			<header className="flex justify-between items-center mb-6 flex-shrink-0">
				<h2 className="text-lg font-semibold text-white flex items-center gap-2">
					{title}
				</h2>
				<button
					onClick={onClose}
					className="p-1.5 rounded-full hover:bg-neutral-700"
				>
					<IconX size={18} />
				</button>
			</header>
			<main className="flex-1 overflow-y-auto custom-scrollbar pr-2 text-left space-y-6">
				{children}
			</main>
		</motion.div>
	</motion.div>
)

const MemoryDetailPanel = ({ memory, onClose, onUpdate, onDelete }) => {
	if (!memory) return null

	const [isEditing, setIsEditing] = useState(false)
	const [editedContent, setEditedContent] = useState(memory.content)
	const [isSaving, setIsSaving] = useState(false)
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
	const [isDeleting, setIsDeleting] = useState(false)

	const timeAgo = formatDistanceToNow(parseISO(memory.created_at), {
		addSuffix: true
	})

	const handleSave = async () => {
		if (editedContent.trim() === memory.content) {
			setIsEditing(false)
			return
		}
		setIsSaving(true)
		await onUpdate(memory.id, editedContent)
		setIsSaving(false)
		setIsEditing(false)
	}

	const handleDeleteConfirm = async () => {
		setIsDeleting(true)
		await onDelete(memory.id)
		// The parent component will handle closing the panel
	}

	return (
		<>
			<motion.div
				key={memory.id}
				initial={{ x: "100%" }}
				animate={{ x: 0 }}
				exit={{ x: "100%" }}
				transition={{ type: "spring", stiffness: 300, damping: 30 }}
				className="fixed inset-0 md:absolute md:top-0 md:right-0 md:inset-auto h-full w-full md:w-[400px] lg:w-[450px] bg-black/50 backdrop-blur-lg md:border-l border-neutral-800 flex flex-col z-50"
			>
				<header className="flex items-start justify-between p-4 border-b border-neutral-800 flex-shrink-0">
					<div className="flex items-center gap-3">
						<IconBrain className="w-6 h-6 text-brand-orange" />
						<h2 className="text-lg font-semibold text-white">
							Memory
						</h2>
					</div>
					<button
						onClick={onClose}
						className="p-1.5 rounded-full text-neutral-400 hover:bg-neutral-700 hover:text-white"
					>
						<IconX size={18} />
					</button>
				</header>
				<main className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
					<div>
						<h3 className="text-sm font-semibold text-neutral-400 mb-2">
							CONTENT
						</h3>
						{isEditing ? (
							<textarea
								value={editedContent}
								onChange={(e) =>
									setEditedContent(e.target.value)
								}
								className="w-full h-40 bg-neutral-900 border border-neutral-700 rounded-lg p-3 text-base text-neutral-200 focus:ring-2 focus:ring-brand-orange"
								autoFocus
							/>
						) : (
							<p className="text-neutral-200 text-base font-sans leading-relaxed whitespace-pre-wrap">
								{memory.content}
							</p>
						)}
					</div>
					<div className="space-y-4">
						<div className="flex items-start gap-3">
							<IconClock
								size={16}
								className="text-neutral-500 mt-0.5"
							/>
							<div>
								<h4 className="text-sm font-semibold text-neutral-400">
									CREATED
								</h4>
								<p className="text-xs text-neutral-300">
									{timeAgo}
								</p>
							</div>
						</div>
						{memory.source && (
							<div className="flex items-start gap-3">
								<IconFileText
									size={16}
									className="text-neutral-500 mt-0.5"
								/>
								<div>
									<h4 className="text-sm font-semibold text-neutral-400">
										SOURCE
									</h4>
									<p className="text-xs text-neutral-300">
										{memory.source}
									</p>
								</div>
							</div>
						)}
						{memory.topics && memory.topics.length > 0 && (
							<div className="flex items-start gap-3">
								<IconTag
									size={16}
									className="text-neutral-500 mt-0.5"
								/>
								<div>
									<h4 className="text-sm font-semibold text-neutral-400">
										TOPICS
									</h4>
									<div className="flex flex-wrap gap-2 mt-1">
										{memory.topics.map((topic) => (
											<span
												key={topic}
												className="bg-neutral-800 px-2 py-0.5 rounded-full text-xs text-neutral-300"
											>
												{topic}
											</span>
										))}
									</div>
								</div>
							</div>
						)}
					</div>
				</main>
				<footer className="p-4 border-t border-neutral-800 flex-shrink-0 flex justify-end gap-2">
					{isEditing ? (
						<>
							<button
								onClick={() => {
									setIsEditing(false)
									setEditedContent(memory.content)
								}}
								className="py-2 px-4 rounded-lg bg-neutral-700 hover:bg-neutral-600 text-sm font-medium"
							>
								Cancel
							</button>
							<button
								onClick={handleSave}
								disabled={isSaving}
								className="py-2 px-4 rounded-lg bg-brand-orange hover:bg-brand-orange/90 text-brand-black font-semibold text-sm flex items-center gap-2"
							>
								{isSaving ? (
									<IconLoader
										size={16}
										className="animate-spin"
									/>
								) : (
									<IconDeviceFloppy size={16} />
								)}
								{isSaving ? "Saving..." : "Save"}
							</button>
						</>
					) : (
						<>
							<button
								onClick={() => setShowDeleteConfirm(true)}
								className="py-2 px-4 rounded-lg bg-red-600/20 hover:bg-red-600/40 text-red-300 text-sm font-medium flex items-center gap-2"
							>
								<IconTrash size={16} /> Delete
							</button>
							<button
								onClick={() => setIsEditing(true)}
								className="py-2 px-4 rounded-lg bg-neutral-700 hover:bg-neutral-600 text-sm font-medium flex items-center gap-2"
							>
								<IconPencil size={16} /> Edit
							</button>
						</>
					)}
				</footer>
			</motion.div>
			<AnimatePresence>
				{showDeleteConfirm && (
					<ModalDialog
						title="Delete Memory"
						description="Are you sure you want to permanently delete this memory? This action cannot be undone."
						confirmButtonText="Delete"
						confirmButtonType="danger"
						onConfirm={handleDeleteConfirm}
						onCancel={() => setShowDeleteConfirm(false)}
						isConfirmDisabled={isDeleting}
					/>
				)}
			</AnimatePresence>
		</>
	)
}

const CreateMemoryModal = ({ isOpen, onClose, onCreate, userDetails }) => {
	const [content, setContent] = useState("")
	const [isSaving, setIsSaving] = useState(false)

	const handleCreate = async () => {
		if (!content.trim()) {
			toast.error("Memory content cannot be empty.")
			return
		}
		setIsSaving(true)
		await onCreate(content)
		setIsSaving(false)
		setContent("") // Reset for next time
	}

	if (!isOpen) return null

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/70 backdrop-blur-md z-[60] flex items-center justify-center p-4"
			onClick={onClose}
		>
			<motion.div
				initial={{ scale: 0.95, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.95, y: -20 }}
				transition={{ duration: 0.2, ease: "easeInOut" }}
				onClick={(e) => e.stopPropagation()}
				className="relative bg-neutral-900/90 backdrop-blur-xl p-6 rounded-2xl shadow-2xl w-full max-w-lg border border-neutral-700 flex flex-col"
			>
				<header className="flex justify-between items-center mb-4 flex-shrink-0">
					<h2 className="text-lg font-semibold text-white">
						Add a New Memory
					</h2>
					<button
						onClick={onClose}
						className="p-1.5 rounded-full hover:bg-neutral-700"
					>
						<IconX size={18} />
					</button>
				</header>
				<main className="flex-1">
					<textarea
						value={content}
						onChange={(e) => setContent(e.target.value)}
						placeholder="Enter a fact or piece of information to remember..."
						className="w-full h-40 bg-neutral-800 border border-neutral-700 rounded-lg p-3 text-base text-neutral-200 focus:ring-2 focus:ring-brand-orange"
						autoFocus
					/>
					<p className="text-xs text-neutral-500 mt-2 px-1">
						Note: All memories should be in the third person. e.g.,
						"
						<span className="font-semibold text-neutral-400">
							{userDetails?.given_name || "User"} likes football
						</span>
						" instead of "I like football".
					</p>
				</main>
				<footer className="mt-6 pt-4 border-t border-neutral-800 flex justify-end gap-2">
					<button
						onClick={onClose}
						className="py-2 px-5 rounded-lg bg-neutral-700 hover:bg-neutral-600 text-sm font-medium"
					>
						Cancel
					</button>
					<button
						onClick={handleCreate}
						disabled={isSaving}
						className="py-2 px-5 rounded-lg bg-brand-orange hover:bg-brand-orange/90 text-brand-black font-semibold text-sm flex items-center gap-2"
					>
						{isSaving ? (
							<IconLoader size={16} className="animate-spin" />
						) : (
							<IconPlus size={16} />
						)}
						{isSaving ? "Saving..." : "Add Memory"}
					</button>
				</footer>
			</motion.div>
		</motion.div>
	)
}

const MemoryCard = ({ memory, onSelect }) => {
	const timeAgo = formatDistanceToNow(parseISO(memory.created_at), {
		addSuffix: true
	})

	return (
		<motion.div
			layout
			initial={{ opacity: 0, scale: 0.9 }}
			animate={{ opacity: 1, scale: 1 }}
			exit={{ opacity: 0, scale: 0.9 }}
			transition={{ duration: 0.3 }}
			onClick={() => onSelect(memory)}
			className="bg-neutral-900/50 p-6 rounded-2xl border border-neutral-800/80 flex flex-col justify-between text-left h-full shadow-lg hover:border-brand-orange/50 transition-colors cursor-pointer"
		>
			<p className="text-neutral-200 text-base mb-4 font-sans leading-relaxed line-clamp-6">
				{memory.content}
			</p>
			<div className="mt-auto pt-4 border-t border-neutral-800/50 text-xs text-neutral-500 space-y-2">
				<div className="flex items-center gap-2">
					<IconClock size={14} />
					<span>{timeAgo}</span>
				</div>
				{memory.source && (
					<div className="flex items-center gap-2">
						<IconFileText size={14} />
						<span>Source: {memory.source}</span>
					</div>
				)}
				{memory.topics && memory.topics.length > 0 && (
					<div className="flex items-center gap-2 flex-wrap pt-1">
						<IconTag size={14} />
						{memory.topics.map((topic) => (
							<span
								key={topic}
								className="bg-neutral-800 px-2 py-0.5 rounded-full text-neutral-300"
							>
								{topic}
							</span>
						))}
					</div>
				)}
			</div>
		</motion.div>
	)
}

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
	ssr: false,
	loading: () => (
		<p className="flex-1 flex justify-center items-center text-neutral-500">
			Loading 3D Graph...
		</p>
	)
})

const MemoryGraph = ({ data, onSelectNode, onClearSelection }) => {
	const fgRef = useRef()

	const graphData = useMemo(() => {
		if (!data) return { nodes: [], links: [] }
		const links = (data.links || data.edges || []).map((edge) => ({
			source: edge.source || edge.from,
			target: edge.target || edge.to,
			...edge
		}))
		const nodes = data.nodes.map((node) => ({
			...node,
			color: node.id % 5 === 0 ? "#22c55e" : "#f59e0b",
			val: 1
		}))
		return { nodes, links }
	}, [data])

	const handleNodeClick = useCallback(
		(node) => {
			const originalNode = data.nodes.find((n) => n.id === node.id)
			if (originalNode) onSelectNode(originalNode)
			const distance = 120
			const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z)
			if (fgRef.current) {
				fgRef.current.cameraPosition(
					{
						x: node.x * distRatio,
						y: node.y * distRatio,
						z: node.z * distRatio
					},
					node,
					1000
				)
			}
		},
		[data.nodes, onSelectNode]
	)

	return (
		<div className="w-full h-full bg-transparent absolute inset-0">
			<ForceGraph3D
				ref={fgRef}
				graphData={graphData}
				backgroundColor="rgba(0,0,0,0)"
				nodeLabel="title"
				nodeVal={4}
				nodeColor="color"
				nodeOpacity={0.8}
				nodeResolution={8}
				linkColor={() => "rgba(74, 158, 255, 1)"}
				linkWidth={2}
				onNodeClick={handleNodeClick}
				onBackgroundClick={onClearSelection}
			/>
		</div>
	)
}

export default function MemoriesPage() {
	const [view, setView] = useState("graph")
	const [memories, setMemories] = useState([])
	const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
	const [isLoading, setIsLoading] = useState(true)
	const [activeTopic, setActiveTopic] = useState("All")
	const [selectedMemory, setSelectedMemory] = useState(null)
	const [isInfoPanelOpen, setIsInfoPanelOpen] = useState(false)
	const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
	const [isUpgradeModalOpen, setUpgradeModalOpen] = useState(false)
	const { isPro } = usePlan()
	const [userDetails, setUserDetails] = useState(null)

	const topics = useMemo(() => {
		const allTopics = new Set()
		memories.forEach((memory) => {
			;(memory.topics || []).forEach((topic) => allTopics.add(topic))
		})
		return ["All", ...Array.from(allTopics).sort()]
	}, [memories])

	const filteredMemories = useMemo(() => {
		if (activeTopic === "All") return memories
		return memories.filter((memory) =>
			(memory.topics || []).includes(activeTopic)
		)
	}, [memories, activeTopic])

	const fetchData = useCallback(async () => {
		setIsLoading(true)
		try {
			if (view === "list") {
				const response = await fetch("/api/memories", {
					cache: "no-store"
				})
				if (!response.ok) throw new Error("Failed to fetch memories.")
				const data = await response.json()
				setMemories(data.memories || [])
			} else {
				const response = await fetch("/api/memories/graph", {
					cache: "no-store"
				})
				if (!response.ok)
					throw new Error("Failed to fetch memory graph data.")
				const data = await response.json()
				setGraphData(data)
				// Also update the flat list for topic filtering consistency
				setMemories(data.nodes || [])
			}
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [view])

	const fetchUserDetails = useCallback(async () => {
		try {
			const res = await fetch("/api/user/profile")
			if (res.ok) {
				const data = await res.json()
				setUserDetails(data)
			} else {
				setUserDetails({ given_name: "User" })
			}
		} catch (error) {
			console.error("Failed to fetch user details:", error)
			setUserDetails({ given_name: "User" })
		}
	}, [])
	useEffect(() => {
		fetchData()
		fetchUserDetails()
	}, [fetchData, fetchUserDetails])

	const handleCreateMemory = async (content) => {
		const toastId = toast.loading("Adding memory...")
		try {
			const res = await fetch("/api/memories", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ content, source: "manual_entry" })
			})
			if (!res.ok) {
				const errorData = await res.json().catch(() => ({}))
				const error = new Error(
					errorData.error || "Failed to add memory"
				)
				error.status = res.status
				throw error
			}
			toast.success("Memory added successfully!", { id: toastId })
			setIsCreateModalOpen(false)
			await fetchData() // Refresh data
		} catch (error) {
			if (error.status === 429) {
				toast.error(
					error.message ||
						"You've reached your memory limit for the free plan.",
					{ id: toastId }
				)
				if (!isPro) {
					setUpgradeModalOpen(true)
					setIsCreateModalOpen(false) // Close the create modal
				}
			} else {
				toast.error(error.message, { id: toastId })
			}
		}
	}

	const handleUpdateMemory = async (memoryId, newContent) => {
		const toastId = toast.loading("Updating memory...")
		try {
			const res = await fetch(`/api/memories/${memoryId}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ content: newContent })
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.error || "Failed to update memory")
			}
			toast.success("Memory updated!", { id: toastId })
			setSelectedMemory(null) // Close panel
			await fetchData() // Refresh data
		} catch (error) {
			toast.error(error.message, { id: toastId })
		}
	}

	const handleDeleteMemory = async (memoryId) => {
		const toastId = toast.loading("Deleting memory...")
		try {
			const res = await fetch(`/api/memories/${memoryId}`, {
				method: "DELETE"
			})
			if (!res.ok) {
				const errorData = await res.json()
				throw new Error(errorData.error || "Failed to delete memory")
			}
			toast.success("Memory deleted.", { id: toastId })
			setSelectedMemory(null) // Close panel
			await fetchData() // Refresh data
		} catch (error) {
			toast.error(error.message, { id: toastId })
		}
	}

	const ViewSwitcher = () => (
		<div className="flex items-center gap-2 p-1 bg-neutral-800/50 rounded-full">
			<button
				onClick={() => setView("graph")}
				className={cn(
					"px-3 py-1.5 rounded-full text-sm font-medium flex items-center gap-2",
					view === "graph"
						? "bg-white text-black"
						: "text-neutral-400 hover:text-white"
				)}
			>
				<IconShare3 size={16} /> Graph
			</button>
			<button
				onClick={() => setView("list")}
				className={cn(
					"px-3 py-1.5 rounded-full text-sm font-medium flex items-center gap-2",
					view === "list"
						? "bg-white text-black"
						: "text-neutral-400 hover:text-white"
				)}
			>
				<IconLayoutGrid size={16} /> List
			</button>
		</div>
	)

	return (
		<div className="flex-1 flex h-screen text-white overflow-hidden">
			<UpgradeToProModal
				isOpen={isUpgradeModalOpen}
				onClose={() => setUpgradeModalOpen(false)}
			/>
			<AnimatePresence>
				{isInfoPanelOpen && (
					<InfoPanel
						onClose={() => setIsInfoPanelOpen(false)}
						title={
							<div className="flex items-center gap-2">
								<IconSparkles /> About Memories
							</div>
						}
					>
						<p className="text-neutral-300">
							This is your memory, a collection of facts and
							information I've learned about you to provide a
							truly personalized experience.
						</p>
						<div className="space-y-4">
							<div className="flex items-start gap-4">
								<IconBrain
									size={20}
									className="text-brand-orange flex-shrink-0 mt-1"
								/>
								<div>
									<h3 className="font-semibold text-white">
										How it Works
									</h3>
									<p className="text-neutral-400 text-sm mt-1">
										As we interact, I identify key pieces of
										information—like your preferences,
										goals, relationships, and interests—and
										store them as individual memories. This
										can happen during our chats or when I
										process information from your connected
										apps.
									</p>
								</div>
							</div>
							<div className="flex items-start gap-4">
								<IconHeart
									size={20}
									className="text-brand-orange flex-shrink-0 mt-1"
								/>
								<div>
									<h3 className="font-semibold text-white">
										How it's Used
									</h3>
									<p className="text-neutral-400 text-sm mt-1">
										I use these memories to provide more
										context-aware assistance. For example,
										if you ask me to 'email my manager', I
										can look up who your manager is from my
										memory instead of asking you every time.
										This makes our interactions faster and
										more intelligent.
									</p>
								</div>
							</div>
						</div>
					</InfoPanel>
				)}
			</AnimatePresence>
			<div className="flex-1 flex flex-col overflow-hidden relative w-full">
				<div className="absolute inset-0 z-[-1] network-grid-background">
					{view === "list" && <InteractiveNetworkBackground />}
				</div>
				<div className="absolute -top-[250px] left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-brand-orange/10 rounded-full blur-3xl -z-10" />

				<header className="flex flex-col md:flex-row md:items-center justify-between p-4 pt-20 md:pt-4 sm:p-6 bg-transparent shrink-0 z-10 border-b border-neutral-800/80">
					<div>
						<h1 className="text-3xl lg:text-4xl font-bold text-white flex items-center gap-3">
							Memories
						</h1>
						<p className="text-neutral-400 mt-1">
							A collection of facts and information I've learned
							about you.
						</p>
					</div>
					<div className="w-full md:w-auto mt-4 md:mt-0 flex justify-center items-center gap-2">
						<ViewSwitcher />
						<button
							onClick={() => setIsInfoPanelOpen(true)}
							className="p-2 rounded-full bg-neutral-800/50 hover:bg-neutral-700/80 text-white"
						>
							<IconInfoCircle size={20} />
						</button>
					</div>
				</header>
				<main className="flex-1 relative overflow-hidden">
					{isLoading ? (
						<div className="w-full h-full flex justify-center items-center">
							<IconLoader className="w-12 h-12 animate-spin text-brand-orange" />
						</div>
					) : view === "graph" ? (
						<div className="w-full h-full">
							<MemoryGraph
								data={graphData}
								onSelectNode={setSelectedMemory}
								onClearSelection={() => setSelectedMemory(null)}
							/>
						</div>
					) : (
						<div className="overflow-y-auto h-full p-6 md:p-10 custom-scrollbar">
							<div className="w-full max-w-7xl mx-auto">
								<div className="flex flex-wrap gap-2 mb-8">
									{topics.map((topic) => (
										<button
											key={topic}
											onClick={() =>
												setActiveTopic(topic)
											}
											className={cn(
												"px-4 py-2 rounded-full text-sm font-medium transition-colors",
												activeTopic === topic
													? "bg-brand-orange text-black"
													: "bg-neutral-800 text-neutral-300 hover:bg-neutral-700 hover:text-white"
											)}
										>
											{topic}
										</button>
									))}
								</div>
								{filteredMemories.length > 0 ? (
									<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
										{filteredMemories.map((memory) => (
											<MemoryCard
												key={memory.id}
												memory={memory}
												onSelect={setSelectedMemory}
											/>
										))}
									</div>
								) : (
									<div className="text-center py-20 text-neutral-500">
										<IconBrain
											size={48}
											className="mx-auto mb-4"
										/>
										<h3 className="text-xl font-semibold text-neutral-300">
											No memories found
										</h3>
										<p>
											{activeTopic === "All"
												? "I haven't learned anything about you yet. Try telling me something in the chat!"
												: `No memories match the topic '${activeTopic}'.`}
										</p>
									</div>
								)}
							</div>
						</div>
					)}
				</main>
			</div>
			<AnimatePresence>
				{selectedMemory && (
					<MemoryDetailPanel
						memory={selectedMemory}
						onClose={() => setSelectedMemory(null)}
						onUpdate={handleUpdateMemory}
						onDelete={handleDeleteMemory}
					/>
				)}
			</AnimatePresence>
			<button
				onClick={() => setIsCreateModalOpen(true)}
				className="fixed bottom-6 right-6 z-40 p-4 bg-brand-orange text-black rounded-full shadow-lg hover:bg-brand-orange/90 transition-transform hover:scale-105"
				aria-label="Add new memory"
			>
				<IconPlus size={24} strokeWidth={2.5} />
			</button>
			<AnimatePresence>
				{isCreateModalOpen && (
					<CreateMemoryModal
						isOpen={isCreateModalOpen}
						onClose={() => setIsCreateModalOpen(false)}
						onCreate={handleCreateMemory}
						userDetails={userDetails}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}
