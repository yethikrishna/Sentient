"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
	IconSearch,
	IconX,
	IconLoader,
	IconChecklist,
	IconMessage,
	IconBrain,
	IconFileText,
	IconArrowRight
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { useRouter } from "next/navigation"
import { formatDistanceToNow, parseISO } from "date-fns"

const useDebounce = (value, delay) => {
	const [debouncedValue, setDebouncedValue] = useState(value)
	useEffect(() => {
		const handler = setTimeout(() => {
			setDebouncedValue(value)
		}, delay)
		return () => {
			clearTimeout(handler)
		}
	}, [value, delay])
	return debouncedValue
}

const ResultItem = ({ item }) => {
	const router = useRouter()
	const handleClick = () => {
		if (item.type === "task") {
			router.push(`/tasks?taskId=${item.task_id}`)
		} else if (item.type === "chat") {
			router.push(`/chat`) // Future enhancement: scroll to message
		} else if (item.type === "memory") {
			router.push(`/memories`) // Future enhancement: open memory detail
		}
	}

	const icons = {
		task: <IconChecklist size={18} className="text-blue-400" />,
		chat: <IconMessage size={18} className="text-green-400" />,
		memory: <IconBrain size={18} className="text-yellow-400" />
	}

	const title =
		item.type === "task"
			? item.name
			: item.type === "chat"
				? item.content
				: item.content

	const timestamp = item.timestamp || item.created_at

	return (
		<button
			onClick={handleClick}
			className="w-full text-left p-3 rounded-lg hover:bg-neutral-700/50 transition-colors flex items-center gap-4"
		>
			<div className="flex-shrink-0">{icons[item.type]}</div>
			<div className="flex-1 overflow-hidden">
				<p className="text-sm text-neutral-100 truncate font-medium">
					{title}
				</p>
				<p className="text-xs text-neutral-400 mt-1">
					{item.type.charAt(0).toUpperCase() + item.type.slice(1)}
					{timestamp &&
						` • ${formatDistanceToNow(parseISO(timestamp), { addSuffix: true })}`}
				</p>
			</div>
			<IconArrowRight
				size={16}
				className="text-neutral-500 flex-shrink-0"
			/>
		</button>
	)
}

export default function GlobalSearch({ onClose }) {
	const [query, setQuery] = useState("")
	const [activeFilter, setActiveFilter] = useState("All")
	const [results, setResults] = useState([])
	const [isLoading, setIsLoading] = useState(false)
	const debouncedQuery = useDebounce(query, 300)

	const filters = ["All", "Tasks", "Chats", "Memories"]

	const fetchResults = useCallback(async (searchQuery) => {
		if (searchQuery.length < 3) {
			setResults([])
			return
		}
		setIsLoading(true)
		try {
			const response = await fetch(
				`/api/search?q=${encodeURIComponent(searchQuery)}`
			)
			if (!response.ok) {
				throw new Error("Search failed")
			}
			const data = await response.json()
			setResults(data.results || [])
		} catch (error) {
			console.error("Search error:", error)
			setResults([])
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchResults(debouncedQuery)
	}, [debouncedQuery, fetchResults])

	const filteredResults = useMemo(() => {
		if (activeFilter === "All") {
			return results
		}
		const filterType = activeFilter.slice(0, -1).toLowerCase() // Tasks -> task
		return results.filter((r) => r.type === filterType)
	}, [results, activeFilter])

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/70 backdrop-blur-md z-[60] flex items-start justify-center p-4 pt-[15vh] md:pt-[20vh]"
			onClick={onClose}
		>
			<motion.div
				initial={{ scale: 0.95, y: -20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.95, y: -20 }}
				transition={{ duration: 0.2, ease: "easeInOut" }}
				onClick={(e) => e.stopPropagation()}
				className="relative bg-neutral-900/80 backdrop-blur-xl p-4 rounded-2xl shadow-2xl w-full max-w-2xl border border-neutral-700 flex flex-col"
			>
				{/* Search Input */}
				<div className="relative flex-shrink-0">
					<IconSearch
						className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-500"
						size={20}
					/>
					<input
						type="text"
						value={query}
						onChange={(e) => setQuery(e.target.value)}
						placeholder="Search tasks, chats, and memories..."
						className="w-full bg-neutral-800/50 border border-neutral-700 rounded-lg pl-12 pr-10 py-3 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-brand-orange"
						autoFocus
					/>
					<button
						onClick={onClose}
						className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-full hover:bg-neutral-700"
					>
						<IconX size={18} />
					</button>
				</div>

				{/* Filters */}
				<div className="flex flex-wrap gap-2 mt-4 px-1 flex-shrink-0">
					{filters.map((filter) => (
						<button
							key={filter}
							onClick={() => setActiveFilter(filter)}
							className={cn(
								"px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
								activeFilter === filter
									? "bg-brand-orange text-black"
									: "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
							)}
						>
							{filter}
						</button>
					))}
				</div>

				{/* Results */}
				<div className="mt-4 pt-4 border-t border-neutral-800 min-h-[200px] max-h-[50vh] overflow-y-auto custom-scrollbar">
					<AnimatePresence mode="wait">
						{isLoading ? (
							<motion.div
								key="loader"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								exit={{ opacity: 0 }}
								className="flex justify-center items-center h-full p-8"
							>
								<IconLoader className="animate-spin text-neutral-500" />
							</motion.div>
						) : filteredResults.length > 0 ? (
							<motion.div
								key="results"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								exit={{ opacity: 0 }}
								className="space-y-1"
							>
								{filteredResults.map((item) => (
									<ResultItem
										key={`${item.type}-${item.task_id || item.message_id || item.id}`}
										item={item}
									/>
								))}
							</motion.div>
						) : (
							<motion.div
								key="empty"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								exit={{ opacity: 0 }}
								className="flex flex-col justify-center items-center text-center h-full p-8 text-neutral-500"
							>
								<IconFileText size={32} className="mb-2" />
								<p className="font-medium text-neutral-400">
									{debouncedQuery.length < 3
										? "Start typing to search"
										: `No results for "${debouncedQuery}"`}
								</p>
								<p className="text-sm">
									{debouncedQuery.length < 3
										? "Search requires at least 3 characters."
										: "Try a different search term."}
								</p>
							</motion.div>
						)}
					</AnimatePresence>
				</div>
			</motion.div>
		</motion.div>
	)
}
