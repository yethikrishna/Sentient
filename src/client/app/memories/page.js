"use client"

import React, { useState, useEffect, useMemo } from "react"
import toast from "react-hot-toast"
import {
	IconLoader,
	IconBrain,
	IconTag,
	IconClock,
	IconFileText
} from "@tabler/icons-react"
import { motion, AnimatePresence } from "framer-motion"
import { formatDistanceToNow, parseISO } from "date-fns"
import { cn } from "@utils/cn"
import { GridBackground } from "@components/ui/GridBackground"

const MemoryCard = ({ memory }) => {
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
			className="bg-neutral-900/50 p-6 rounded-2xl border border-neutral-800/80 flex flex-col justify-between text-left h-full shadow-lg hover:border-sentient-blue/30 transition-colors"
		>
			<p className="text-neutral-200 text-base mb-4 font-sans leading-relaxed">
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

const MemoriesPage = () => {
	const [memories, setMemories] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [activeTopic, setActiveTopic] = useState("All")

	useEffect(() => {
		const fetchMemories = async () => {
			setIsLoading(true)
			try {
				const response = await fetch("/api/memories")
				if (!response.ok) {
					throw new Error("Failed to fetch memories.")
				}
				const data = await response.json()
				setMemories(data.memories || [])
			} catch (error) {
				toast.error(error.message)
			} finally {
				setIsLoading(false)
			}
		}
		fetchMemories()
	}, [])

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

	return (
		<div className="flex-1 flex h-screen bg-brand-black text-white overflow-hidden md:pl-20">
			<GridBackground className="flex-1 flex flex-col overflow-hidden relative">
				<header className="flex items-center justify-between p-6 bg-brand-black/50 backdrop-blur-sm border-b border-neutral-800/50 shrink-0 z-10">
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
				</header>
				<main className="flex-1 overflow-y-auto p-6 md:p-10 custom-scrollbar">
					{isLoading ? (
						<div className="flex justify-center items-center h-full">
							<IconLoader className="w-12 h-12 animate-spin text-sentient-blue" />
						</div>
					) : (
						<div className="w-full max-w-7xl mx-auto">
							<div className="flex flex-wrap gap-2 mb-8 sticky top-0 bg-brand-black/50 backdrop-blur-sm py-4 z-10 rounded-b-xl -mt-2">
								{topics.map((topic) => (
									<button
										key={topic}
										onClick={() => setActiveTopic(topic)}
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
									<AnimatePresence>
										{filteredMemories.map((memory) => (
											<MemoryCard
												key={memory.id}
												memory={memory}
											/>
										))}
									</AnimatePresence>
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
					)}
				</main>
			</GridBackground>
		</div>
	)
}

export default MemoriesPage
