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
	IconShare3
} from "@tabler/icons-react"
import { motion, AnimatePresence } from "framer-motion"
import { formatDistanceToNow, parseISO } from "date-fns"
import { cn } from "@utils/cn"
import InteractiveNetworkBackground from "@components/ui/InteractiveNetworkBackground"
import { Network } from "vis-network/standalone/esm/vis-network"

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
			className="absolute top-0 right-0 h-full w-full md:w-[400px] lg:w-[450px] bg-black/50 backdrop-blur-lg border-l border-neutral-800 flex flex-col z-20"
		>
			<header className="flex items-start justify-between p-4 border-b border-neutral-800 flex-shrink-0">
				<div className="flex items-center gap-3">
					<IconBrain className="w-6 h-6 text-sentient-blue" />
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
			onClick={() => onSelect(memory)}
			className="bg-neutral-900/50 p-6 rounded-2xl border border-neutral-800/80 flex flex-col justify-between text-left h-full shadow-lg hover:border-sentient-blue/30 transition-colors cursor-pointer"
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

const MemoryGraph = ({ data, onSelectNode, onClearSelection }) => {
	const containerRef = useRef(null)

	useEffect(() => {
		if (!containerRef.current || !data || data.nodes.length === 0) return

		const options = {
			nodes: {
				shape: "dot",
				size: 12,
				font: {
					size: 14,
					color: "#ffffff"
				},
				borderWidth: 2,
				color: {
					border: "#252525",
					background: "#F1A21D",
					highlight: {
						border: "#FFFFFF",
						background: "#4a9eff"
					}
				}
			},
			edges: {
				width: 0.5,
				color: {
					color: "#848484",
					highlight: "#4a9eff"
				},
				arrows: {
					to: { enabled: false }
				},
				smooth: {
					type: "continuous"
				}
			},
			physics: {
				enabled: true,
				solver: "forceAtlas2Based",
				forceAtlas2Based: {
					gravitationalConstant: -50,
					centralGravity: 0.01,
					springLength: 230,
					springConstant: 0.08
				},
				stabilization: {
					iterations: 150
				}
			},
			interaction: {
				hover: true,
				tooltipDelay: 200
			},
			layout: {
				randomSeed: 42
			}
		}

		const network = new Network(containerRef.current, data, options)

		network.on("selectNode", (params) => {
			if (params.nodes.length > 0) {
				const nodeId = params.nodes[0]
				const node = data.nodes.find((n) => n.id === nodeId)
				if (node) {
					onSelectNode(node)
				}
			}
		})

		network.on("deselectNode", () => {
			onClearSelection()
		})

		return () => {
			network.destroy()
		}
	}, [data, onSelectNode, onClearSelection])

	return <div ref={containerRef} className="w-full h-full" />
}

export default function MemoriesPage() {
	const [view, setView] = useState("graph") // 'graph' or 'list'
	const [memories, setMemories] = useState([])
	const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
	const [isLoading, setIsLoading] = useState(true)
	const [activeTopic, setActiveTopic] = useState("All")
	const [selectedMemory, setSelectedMemory] = useState(null)

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
				const response = await fetch("/api/memories/graph")
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
		<div className="flex-1 flex h-screen bg-brand-black text-white overflow-hidden relative">
			<div className="flex-1 flex flex-col overflow-hidden relative">
				<header className="flex items-center justify-between p-4 sm:p-6 bg-transparent shrink-0 z-10 absolute top-0 left-0 right-0">
					<div>
						<h1 className="text-3xl lg:text-4xl font-bold text-white flex items-center gap-3">
							<IconBrain
								size={36}
								className="text-sentient-blue"
							/>
							Your Memories
						</h1>
						<p className="text-neutral-400 mt-1">
							A collection of facts and information I've learned
							about you.
						</p>
					</div>
					<ViewSwitcher />
				</header>
				<main className="flex-1 w-full h-full relative">
					<div className="absolute inset-0 z-[-1]">
						<InteractiveNetworkBackground />
					</div>
					{isLoading ? (
						<div className="w-full h-full flex justify-center items-center">
							<IconLoader className="w-12 h-12 animate-spin text-sentient-blue" />
						</div>
					) : view === "graph" ? (
						<MemoryGraph
							data={graphData}
							onSelectNode={setSelectedMemory}
							onClearSelection={() => setSelectedMemory(null)}
						/>
					) : (
						<div className="overflow-y-auto h-full p-6 md:p-10 pt-32 custom-scrollbar">
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
													? "bg-white text-black shadow-lg shadow-white/10"
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
