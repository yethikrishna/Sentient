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
	IconHeart
} from "@tabler/icons-react"
import { motion, AnimatePresence } from "framer-motion"
import { formatDistanceToNow, parseISO } from "date-fns"
import { cn } from "@utils/cn"
import dynamic from "next/dynamic"
import InteractiveNetworkBackground from "@components/ui/InteractiveNetworkBackground"

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

const MemoryDetailPanel = ({ memory, onClose }) => {
	if (!memory) return null

	const timeAgo = formatDistanceToNow(parseISO(memory.created_at), {
		addSuffix: true
	})

	return (
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
					<h2 className="text-lg font-semibold text-white">Memory</h2>
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
					<p className="text-neutral-200 text-base font-sans leading-relaxed whitespace-pre-wrap">
						{memory.content}
					</p>
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
			onClick={() => onSelect(memory)} // prettier-ignore
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
			color: node.id % 5 === 0 ? "#22c55e" : "#f59e0b", // green-500 or amber-500
			val: 1 // a small default size
		}))

		return { nodes, links }
	}, [data])

	const handleNodeClick = useCallback(
		(node) => {
			const originalNode = data.nodes.find((n) => n.id === node.id)
			if (originalNode) {
				onSelectNode(originalNode)
			}

			const distance = 120
			const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z)
			if (fgRef.current) {
				fgRef.current.cameraPosition(
					{
						x: node.x * distRatio,
						y: node.y * distRatio,
						z: node.z * distRatio
					},
					node, // lookAt
					1000 // transition duration
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
	const [view, setView] = useState("graph") // 'graph' or 'list'
	const [memories, setMemories] = useState([])
	const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
	const [isLoading, setIsLoading] = useState(true)
	const [activeTopic, setActiveTopic] = useState("All")
	const [selectedMemory, setSelectedMemory] = useState(null)
	const [isInfoPanelOpen, setIsInfoPanelOpen] = useState(false)

	const topics = useMemo(() => {
		const allTopics = new Set()
		memories.forEach((memory) => {
			memory.topics.forEach((topic) => allTopics.add(topic))
		})
		return ["All", ...Array.from(allTopics).sort()]
	}, [memories])

	const filteredMemories = useMemo(() => {
		if (activeTopic === "All") {
			return memories
		}
		return memories.filter((memory) => memory.topics.includes(activeTopic))
	}, [memories, activeTopic])

	const fetchData = useCallback(async () => {
		setIsLoading(true)
		setSelectedMemory(null)
		try {
			if (view === "list") {
				const response = await fetch("/api/memories")
				if (!response.ok) throw new Error("Failed to fetch memories.")
				const data = await response.json()
				setMemories(data.memories || [])
			} else {
				const response = await fetch("/api/memories/graph/")
				if (!response.ok)
					throw new Error("Failed to fetch memory graph data.")
				const data = await response.json()
				setGraphData(data)
			}
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [view])

	useEffect(() => {
		fetchData()
	}, [fetchData])

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
							This is your long-term memory, a collection of facts
							and information I've learned about you to provide a
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
							<IconBrain
								size={36}
								className="text-brand-orange"
							/>
							Your Memories
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
					/>
				)}
			</AnimatePresence>
		</div>
	)
}
