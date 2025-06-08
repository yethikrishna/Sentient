// src/client/app/memory/page.js
"use client"

import React, { useEffect, useState, useCallback } from "react"
import GraphVisualization from "@components/GraphViz"
import Sidebar from "@components/Sidebar"
import { IconRefresh, IconSettingsCog, IconLoader } from "@tabler/icons-react"
import toast from "react-hot-toast"
import ProIcon from "@components/ProIcon"
import ShortTermMemoryDisplay from "@components/ShortTermMemoryDisplay"
import MemoryTypeSwitcher from "@components/MemoryTypeSwitcher"

const Memories = () => {
	const [userDetails, setUserDetails] = useState(null)
	const [isSidebarVisible, setSidebarVisible] = useState(false)
	const [isCustomizeInputVisible, setCustomizeInputVisible] = useState(false)
	const [memoryInstruction, setMemoryInstruction] = useState("")
	const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
	const [addMemoriesLoading, setAddMemoriesLoading] = useState(false)
	const [recreateGraphLoading, setRecreateGraphLoading] = useState(false)
	const [pricing, setPricing] = useState("free")
	const [credits, setCredits] = useState(0)
	const [memoryDisplayType, setMemoryDisplayType] = useState("long-term")
	const [graphLoading, setGraphLoading] = useState(false)
	const [refreshShortTerm, setRefreshShortTerm] = useState(0)

	// --- Data Fetching ---
	const fetchUserDetails = async () => {
		try {
			const response = await fetch("/api/user/profile")
			if (!response.ok) throw new Error("Failed to fetch user details")
			setUserDetails(await response.json())
		} catch (error) {
			toast.error(`Error fetching user details: ${error.message}`)
		}
	}

	const fetchPricingPlan = async () => {
		try {
			const response = await fetch("/api/user/pricing")
			if (!response.ok) throw new Error("Failed to fetch pricing plan")
			const data = await response.json()
			setPricing(data.pricing || "free")
			setCredits(data.credits || 0)
		} catch (error) {
			toast.error(`Error fetching pricing plan: ${error.message}`)
		}
	}

	const loadGraphData = useCallback(async () => {
		setGraphLoading(true)
		setGraphData({ nodes: [], edges: [] })
		try {
			const response = await fetch("/api/memory/long-term")
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Unknown API error")
			}
			if (data.nodes && data.edges) {
				setGraphData({ nodes: data.nodes, edges: data.edges })
			} else {
				setGraphData({ nodes: [], edges: [] })
				toast.error("Received invalid graph data format from API.")
			}
		} catch (error) {
			toast.error(`Error loading graph data: ${error.message}`)
			setGraphData({ nodes: [], edges: [] })
		} finally {
			setGraphLoading(false)
		}
	}, [])

	// --- Action Handlers ---
	const handleRecreateGraph = async () => {
		setRecreateGraphLoading(true)
		try {
			const response = await fetch("/api/memory/long-term/reset", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ clear_graph: true })
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Unknown API error")
			}
			loadGraphData() // Re-fetch data
			toast.success("Graph recreated successfully!")
		} catch (error) {
			toast.error(`Error recreating memories: ${error.message}`)
		} finally {
			setRecreateGraphLoading(false)
		}
	}

	const handleCustomizeGraph = async () => {
		if (!memoryInstruction.trim()) {
			toast.error("Information cannot be empty.")
			return
		}
		setAddMemoriesLoading(true)
		try {
			const response = await fetch("/api/memory/long-term/customize", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ information: memoryInstruction })
			})
			const result = await response.json()
			if (!response.ok) {
				throw new Error(result.error || "Unknown API error")
			}

			// Refresh the current view
			if (memoryDisplayType === "long-term") {
				loadGraphData()
			} else {
				setRefreshShortTerm((prev) => prev + 1)
			}

			setMemoryInstruction("")
			toast.success("Graph customized successfully!")
		} catch (error) {
			toast.error(`Error customizing graph: ${error.message}`)
		} finally {
			setAddMemoriesLoading(false)
			setCustomizeInputVisible(false)
		}
	}

	useEffect(() => {
		fetchUserDetails()
		fetchPricingPlan()

		if (memoryDisplayType === "long-term") {
			loadGraphData()
		}
	}, [loadGraphData, memoryDisplayType, refreshShortTerm])

	// --- JSX ---
	return (
		<div className="h-screen bg-matteblack flex relative overflow-hidden dark">
			<Sidebar
				userDetails={userDetails}
				isSidebarVisible={isSidebarVisible}
				setSidebarVisible={setSidebarVisible}
			/>
			<div className="flex-grow flex flex-col h-full bg-matteblack text-white relative overflow-hidden p-6 gap-4">
				<div className="flex justify-between items-center px-4 pt-2 flex-shrink-0">
					<h1 className="font-Poppins text-white text-4xl font-light">
						Memories
					</h1>
					<MemoryTypeSwitcher
						currentType={memoryDisplayType}
						onTypeChange={setMemoryDisplayType}
					/>
				</div>
				<div className="flex-grow w-full relative overflow-hidden rounded-lg bg-neutral-900/30 border border-neutral-800 shadow-inner">
					{memoryDisplayType === "long-term" ? (
						<>
							{graphLoading && (
								<div className="absolute inset-0 flex items-center justify-center bg-matteblack/80 z-10">
									<IconLoader className="w-8 h-8 animate-spin text-lightblue" />
									<span className="ml-3 text-lg">
										Loading Knowledge Graph...
									</span>
								</div>
							)}
							<GraphVisualization
								nodes={graphData.nodes}
								edges={graphData.edges}
							/>
						</>
					) : (
						<ShortTermMemoryDisplay
							userDetails={userDetails}
							refreshTrigger={refreshShortTerm}
						/>
					)}
				</div>
				<div className="absolute bottom-6 right-6 flex flex-col items-end space-y-3 z-40">
					{isCustomizeInputVisible &&
						(pricing === "free" || credits > 0) && (
							<div className="bg-neutral-800 p-4 rounded-lg shadow-lg w-96 space-y-3 border border-neutral-700">
								<textarea
									className="w-full p-2.5 border border-neutral-600 rounded-md bg-neutral-700 text-white resize-none h-24 focus:outline-none focus:border-lightblue text-sm"
									placeholder="Tell me what to remember or forget... e.g., 'My best friend's name is Alex' or 'Forget the reminder about the meeting.'"
									value={memoryInstruction}
									onChange={(e) =>
										setMemoryInstruction(e.target.value)
									}
								/>
								<button
									className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition text-sm font-medium disabled:opacity-50"
									onClick={handleCustomizeGraph}
									disabled={
										addMemoriesLoading ||
										!memoryInstruction.trim()
									}
								>
									{addMemoriesLoading ? (
										<IconLoader className="w-5 h-5 animate-spin mx-auto" />
									) : (
										"Submit to Memory Agent"
									)}
								</button>
							</div>
						)}
					<div>
						{/* CHANGE THIS IN PROD TO CHECK PRICING FOR PRO INSTEAD OF FREE */}
						{pricing === "free" || credits > 0 ? (
							<button
								onClick={() =>
									setCustomizeInputVisible((prev) => !prev)
								}
								className="flex items-center gap-2 py-2 px-4 rounded-full bg-darkblue hover:bg-lightblue text-white text-sm font-medium transition-colors shadow-md"
							>
								<IconSettingsCog className="w-5 h-5" />
								{isCustomizeInputVisible
									? "Cancel"
									: "Use Memory Agent"}
							</button>
						) : (
							<button
								disabled
								className="relative flex items-center justify-center py-2 px-4 rounded-full font-medium text-white text-sm bg-neutral-700 cursor-not-allowed opacity-60 shadow-md"
							>
								<IconSettingsCog className="w-5 h-5 mr-2" />
								Use Memory Agent{" "}
								{pricing === "free" && (
									<ProIcon className="ml-1.5" />
								)}
							</button>
						)}
					</div>

					{memoryDisplayType === "long-term" && (
						<button
							className="flex items-center gap-2 py-2 px-4 rounded-full bg-red-600 hover:bg-red-500 text-white text-sm font-medium transition-colors shadow-md disabled:opacity-50"
							onClick={handleRecreateGraph}
							disabled={recreateGraphLoading || graphLoading}
						>
							{recreateGraphLoading ? (
								<IconLoader className="w-5 h-5 animate-spin" />
							) : (
								<IconRefresh className="w-5 h-5" />
							)}
							{recreateGraphLoading
								? "Resetting..."
								: "Reset Long-Term"}
						</button>
					)}
				</div>
			</div>
		</div>
	)
}

export default Memories
