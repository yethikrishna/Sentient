"use client"

import React, { useState, useEffect, useCallback } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import toast from "react-hot-toast"
import { IconLoader, IconFolder, IconArrowLeft } from "@tabler/icons-react"
import Link from "next/link"
import ProjectSidebar from "@components/projects/ProjectSidebar"
import ProjectChatView from "@components/projects/ProjectChatView"
import ProjectTasksView from "@components/projects/ProjectTasksView"
import MembersAndContextPanel from "@components/projects/MembersAndContextPanel"

export default function ProjectPage() {
	const params = useParams()
	const router = useRouter()
	const searchParams = useSearchParams()
	const { projectId } = params

	// State for the main view
	const [activeView, setActiveView] = useState("chat") // 'chat' or 'tasks'
	const [activeChatId, setActiveChatId] = useState(null)

	const [project, setProject] = useState(null)
	const [isLoading, setIsLoading] = useState(true)
	const [error, setError] = useState(null)

	// Separate function for refetching data without a full loading state
	const refetchProjectDetails = useCallback(async () => {
		if (!projectId) return
		try {
			const res = await fetch(`/api/projects/${projectId}`)
			if (!res.ok) throw new Error("Failed to refresh project data")
			const data = await res.json()
			setProject(data)
		} catch (err) {
			toast.error(err.message)
		}
	}, [projectId])

	useEffect(() => {
		const fetchInitialData = async () => {
			if (!projectId) return
			setIsLoading(true)
			setError(null)
			try {
				const res = await fetch(`/api/projects/${projectId}`)
				if (!res.ok) {
					const errorData = await res.json()
					throw new Error(errorData.error || `Project not found`)
				}
				const data = await res.json()
				setProject(data)
				// Set the initial active chat only on the first load
				if (data.chats && data.chats.length > 0) {
					setActiveChatId(data.chats[0].chat_id)
					setActiveView("chat")
				}
			} catch (err) {
				toast.error(err.message)
				setError(err.message)
			} finally {
				setIsLoading(false)
			}
		}
		fetchInitialData()
	}, [projectId])

	const handleChatSelect = (chatId) => {
		setActiveView("chat")
		setActiveChatId(chatId)
	}

	const handleNewChat = () => {
		// For now, this just resets the view. The chat component will handle creation.
		setActiveView("chat")
		setActiveChatId(null)
	}

	// Callback for when a new chat is created by sending the first message
	const handleChatCreated = (newChatSession) => {
		const { chatId, tempTitle } = newChatSession
		setActiveChatId(chatId)

		// Optimistically update the project state to include the new chat
		// This avoids a full refetch which can interrupt the stream.
		setProject((prevProject) => {
			if (
				!prevProject ||
				(prevProject.chats || []).some((c) => c.chat_id === chatId)
			) {
				return prevProject
			}
			const newChat = {
				chat_id: chatId,
				title: tempTitle || "New Chat",
				updated_at: new Date().toISOString()
			}
			return {
				...prevProject,
				chats: [newChat, ...(prevProject.chats || [])]
			}
		})
	}

	if (isLoading) {
		return (
			<div className="flex-1 flex justify-center items-center bg-black md:pl-20">
				<IconLoader
					className="animate-spin text-neutral-500"
					size={32}
				/>
			</div>
		)
	}

	if (error) {
		return (
			<div className="flex-1 flex flex-col justify-center items-center bg-black md:pl-20 text-center">
				<h2 className="text-xl font-semibold text-red-400">
					Error loading project
				</h2>
				<p className="text-neutral-400">{error}</p>
				<Link
					href="/projects"
					className="mt-4 text-blue-400 hover:underline"
				>
					Go back to projects
				</Link>
			</div>
		)
	}

	return (
		<div className="flex-1 flex bg-black text-white overflow-hidden md:pl-20">
			<ProjectSidebar
				project={project}
				activeView={activeView}
				onViewChange={setActiveView}
				activeChatId={activeChatId}
				onChatSelect={handleChatSelect}
				onNewChat={handleNewChat}
			/>
			<div className="flex-1 flex flex-col bg-neutral-900 min-w-0">
				{/* Center Panel: Will hold Chat or Tasks */}
				{activeView === "chat" && (
					<ProjectChatView
						project={project}
						activeChatId={activeChatId}
						onChatCreated={handleChatCreated}
						onNewMessage={refetchProjectDetails} // Refetch project to update chat list (e.g., last message preview)
					/>
				)}
				{activeView === "tasks" && (
					<ProjectTasksView projectId={projectId} />
				)}
			</div>
			<MembersAndContextPanel
				project={project}
				onDataChange={refetchProjectDetails}
			/>
		</div>
	)
}
