"use client"

import React, { useState, useEffect, useCallback } from "react"
import toast from "react-hot-toast"
import { IconLoader, IconPlus } from "@tabler/icons-react"
import AddTaskModal from "@components/tasks/AddTaskModal" // Reusing the existing modal
import { TaskListItem } from "@components/tasks/TaskListItem" // Reusing the list item

const ProjectTasksView = ({ projectId }) => {
	const [tasks, setTasks] = useState([])
	const [isLoading, setIsLoading] = useState(true)
	const [isAddTaskModalOpen, setAddTaskModalOpen] = useState(false)

	const fetchTasks = useCallback(async () => {
		if (!projectId) return
		setIsLoading(true)
		try {
			const res = await fetch(`/api/projects/${projectId}/tasks`)
			if (!res.ok) throw new Error("Failed to fetch project tasks")
			const data = await res.json()
			setTasks(data.tasks || [])
		} catch (error) {
			toast.error(error.message)
		} finally {
			setIsLoading(false)
		}
	}, [projectId])

	useEffect(() => {
		fetchTasks()
	}, [fetchTasks])

	const handleTaskAdded = () => {
		fetchTasks() // Refetch tasks when a new one is added
	}

	const handleAddTask = async (prompt) => {
		try {
			const response = await fetch("/api/tasks/add", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ prompt, project_id: projectId }) // Add project_id
			})
			const data = await response.json()
			if (!response.ok) {
				throw new Error(data.error || "Failed to add task")
			}
			toast.success(data.message || "Task added!")
			handleTaskAdded()
			return true // Indicate success
		} catch (error) {
			toast.error(`Error: ${error.message}`)
			return false // Indicate failure
		}
	}

	return (
		<div className="flex flex-col h-full">
			<header className="flex items-center justify-between p-4 border-b border-neutral-800">
				<h3 className="text-lg font-semibold text-white">
					Project Tasks
				</h3>
				<button
					onClick={() => setAddTaskModalOpen(true)}
					className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
				>
					<IconPlus size={14} />
					New Task
				</button>
			</header>
			<div className="flex-1 overflow-y-auto custom-scrollbar p-4">
				{isLoading ? (
					<div className="flex justify-center items-center h-full">
						<IconLoader className="animate-spin text-neutral-500" />
					</div>
				) : tasks.length === 0 ? (
					<p className="text-center text-sm text-neutral-500">
						No tasks in this project yet.
					</p>
				) : (
					<div className="space-y-2">
						{tasks.map((task) => (
							<TaskListItem
								key={task.task_id}
								task={task}
								onViewDetails={() => {
									/* Implement navigation to task detail view if needed */
								}}
								activeTab="oneTime"
							/>
						))}
					</div>
				)}
			</div>
			{isAddTaskModalOpen && (
				<AddTaskModal
					onClose={() => setAddTaskModalOpen(false)}
					onTaskAdded={handleTaskAdded}
					projectId={projectId} // Pass projectId to the modal
				/>
			)}
		</div>
	)
}

export default ProjectTasksView
