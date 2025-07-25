"use client"

import React, { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import toast from "react-hot-toast"
import {
	IconLoader,
	IconPlus,
	IconFolder,
	IconUsers,
	IconChevronRight
} from "@tabler/icons-react"
import { motion, AnimatePresence } from "framer-motion"
import CreateProjectModal from "@components/projects/CreateProjectModal"

const ProjectCard = ({ project }) => {
	const router = useRouter()
	return (
		<motion.div
			layout
			initial={{ opacity: 0, scale: 0.9 }}
			animate={{ opacity: 1, scale: 1 }}
			exit={{ opacity: 0, scale: 0.9 }}
			onClick={() => router.push(`/projects/${project.project_id}`)}
			className="bg-neutral-900/50 p-6 rounded-2xl border border-neutral-800/80 flex flex-col justify-between text-left h-full cursor-pointer hover:border-blue-500/50 transition-colors group"
		>
			<div>
				<div className="flex items-center gap-3 mb-3">
					<div className="p-2 bg-neutral-800 rounded-lg">
						<IconFolder className="text-blue-400" />
					</div>
					<h3 className="font-semibold text-white text-lg truncate">
						{project.name}
					</h3>
				</div>
				<p className="text-neutral-400 text-sm mb-4 line-clamp-2 h-10">
					{project.description || "No description provided."}
				</p>
			</div>
			<div className="flex items-center justify-between text-xs text-neutral-500 mt-4 pt-4 border-t border-neutral-800">
				<span>Owner: {project.owner_id.substring(0, 15)}...</span>
				<div className="flex items-center gap-2 text-neutral-300 group-hover:text-white">
					View Project{" "}
					<IconChevronRight
						size={14}
						className="transition-transform group-hover:translate-x-1"
					/>
				</div>
			</div>
		</motion.div>
	)
}

export default function ProjectsPage() {
	const [projects, setProjects] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [isCreateModalOpen, setCreateModalOpen] = useState(false)

	const fetchProjects = useCallback(async () => {
		setIsLoading(true)
		try {
			const res = await fetch("/api/projects")
			if (!res.ok) throw new Error("Failed to fetch projects")
			const data = await res.json()
			setProjects(data.projects || [])
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [])

	useEffect(() => {
		fetchProjects()
	}, [fetchProjects])

	return (
		<div className="flex-1 flex flex-col bg-black text-white overflow-hidden md:pl-20">
			<header className="flex items-center justify-between p-6 border-b border-neutral-800/50 shrink-0">
				<h1 className="text-3xl font-bold text-white flex items-center gap-3">
					<IconFolder />
					Projects
				</h1>
				<button
					onClick={() => setCreateModalOpen(true)}
					className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
				>
					<IconPlus size={16} />
					Create Project
				</button>
			</header>

			<main className="flex-1 overflow-y-auto p-6 custom-scrollbar">
				{isLoading ? (
					<div className="flex justify-center items-center h-full">
						<IconLoader
							className="animate-spin text-neutral-500"
							size={32}
						/>
					</div>
				) : projects.length === 0 ? (
					<div className="flex flex-col items-center justify-center h-full text-center text-neutral-500">
						<IconUsers size={48} className="mb-4" />
						<h2 className="text-xl font-semibold text-neutral-300">
							No Projects Yet
						</h2>
						<p>
							Create a project to start collaborating with your
							team.
						</p>
					</div>
				) : (
					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
						<AnimatePresence>
							{projects.map((project) => (
								<ProjectCard
									key={project.project_id}
									project={project}
								/>
							))}
						</AnimatePresence>
					</div>
				)}
			</main>

			<AnimatePresence>
				{isCreateModalOpen && (
					<CreateProjectModal
						onClose={() => setCreateModalOpen(false)}
						onProjectCreated={fetchProjects}
					/>
				)}
			</AnimatePresence>
		</div>
	)
}
