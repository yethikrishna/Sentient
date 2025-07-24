"use client"

import React, { useState, useEffect } from "react"
import {
	IconX,
	IconPencil,
	IconTrash,
	IconRepeat,
	IconDeviceFloppy,
	IconSquareX,
	IconPlayerPlay,
	IconArchive,
	IconCircleCheck,
	IconClipboardList
} from "@tabler/icons-react"
import TaskDetailsContent from "./TaskDetailsContent"
import { cn } from "@utils/cn"

const TaskDetailsPanel = ({
	task,
	allTools,
	integrations,
	onClose,
	onSave,
	onApprove,
	onDelete,
	onRerun,
	onAnswerClarifications,
	onArchiveTask,
	onMarkComplete,
	className,
	onSendChatMessage
}) => {
	const [isEditing, setIsEditing] = useState(false)
	const [editableTask, setEditableTask] = useState(task)

	useEffect(() => {
		setEditableTask(task)
		if (!task) {
			setIsEditing(false) // Reset editing state when task is closed/changed
		}
	}, [task])

	const handleFieldChange = (field, value) =>
		setEditableTask((prev) => ({ ...prev, [field]: value }))
	const handleScheduleChange = (newSchedule) =>
		setEditableTask((prev) => ({ ...prev, schedule: newSchedule }))
	const handleAddStep = () =>
		setEditableTask((prev) => ({
			...prev,
			plan: [...(prev.plan || []), { tool: "", description: "" }]
		}))
	const handleRemoveStep = (index) =>
		setEditableTask((prev) => ({
			...prev,
			plan: prev.plan.filter((_, i) => i !== index)
		}))
	const handleStepChange = (index, field, value) =>
		setEditableTask((prev) => ({
			...prev,
			plan: prev.plan.map((step, i) =>
				i === index ? { ...step, [field]: value } : step
			)
		}))
	const handleSaveEdit = () => {
		onSave(editableTask)
		setIsEditing(false)
	}

	const ActionButton = ({ onClick, icon, children, className = "" }) => (
		<button
			onClick={onClick}
			className={cn(
				"flex items-center gap-2 text-sm px-3 py-2 rounded-lg transition-colors",
				className
			)}
		>
			{icon}
			<span>{children}</span>
		</button>
	)

	return (
		<aside
			className={cn(
				"w-full max-w-2xl bg-neutral-900/80 backdrop-blur-xl shadow-2xl md:border-l border-neutral-700/80 flex flex-col flex-shrink-0",
				className
			)}
		>
			{!task ? (
				<div className="flex flex-col items-center justify-center h-full text-center text-neutral-500 p-8">
					<IconClipboardList size={48} className="mb-4" />
					<h3 className="text-lg font-semibold text-neutral-400">
						Select a Task
					</h3>
					<p className="max-w-xs">
						Choose a task from the list to see its details, plan,
						and outcome here.
					</p>
				</div>
			) : (
				<>
					{/* --- HEADER --- */}
					<header className="flex items-start justify-between p-6 border-b border-neutral-700/50 flex-shrink-0">
						<div className="flex-1">
							{isEditing ? (
								<input
									type="text"
									value={editableTask.description}
									onChange={(e) =>
										handleFieldChange(
											"description",
											e.target.value
										)
									}
									className="w-full bg-transparent text-2xl font-bold text-white focus:ring-0 focus:border-blue-500 border-b-2 border-transparent"
								/>
							) : (
								<h2 className="text-2xl font-bold text-white leading-snug">
									{task.description}
								</h2>
							)}
						</div>
						<button
							onClick={onClose}
							className="ml-4 p-2 rounded-full text-neutral-400 hover:bg-neutral-700 hover:text-white"
						>
							<IconX size={20} />
						</button>
					</header>

					{/* --- CONTENT --- */}
					<main className="flex-1 overflow-y-auto custom-scrollbar p-6">
						<TaskDetailsContent
							task={task}
							isEditing={isEditing}
							editableTask={editableTask}
							handleFieldChange={handleFieldChange}
							handleScheduleChange={handleScheduleChange}
							handleAddStep={handleAddStep}
							handleRemoveStep={handleRemoveStep}
							handleStepChange={handleStepChange}
							allTools={allTools}
							integrations={integrations}
							onAnswerClarifications={onAnswerClarifications}
							onSendChatMessage={onSendChatMessage}
						/>
					</main>

					{/* --- FOOTER --- */}
					<footer className="flex items-center justify-between p-4 border-t border-neutral-700/50 flex-shrink-0 bg-neutral-900/50">
						{isEditing ? (
							<>
								<div className="flex items-center gap-2">
									{/* Empty div for spacing */}
								</div>
								<div className="flex items-center gap-2">
									<ActionButton
										onClick={() => setIsEditing(false)}
										icon={<IconSquareX size={16} />}
										className="bg-neutral-700 text-neutral-200 hover:bg-neutral-600"
									>
										Cancel
									</ActionButton>
									<ActionButton
										onClick={handleSaveEdit}
										icon={<IconDeviceFloppy size={16} />}
										className="bg-blue-600 text-white hover:bg-blue-500"
									>
										Save
									</ActionButton>
								</div>
							</>
						) : (
							<>
								<div className="flex items-center gap-2">
									<ActionButton
										onClick={() => setIsEditing(true)}
										icon={<IconPencil size={16} />}
										className="text-neutral-400 hover:bg-neutral-700 hover:text-white"
									/>
									<ActionButton
										onClick={() => onDelete(task.task_id)}
										icon={<IconTrash size={16} />}
										className="text-neutral-400 hover:bg-red-500/20 hover:text-red-400"
									/>
									<ActionButton
										onClick={() => onRerun(task.task_id)}
										icon={<IconRepeat size={16} />}
										className="text-neutral-400 hover:bg-neutral-700 hover:text-white"
									/>
								</div>
								<div className="flex items-center gap-2">
									{task.status === "approval_pending" && (
										<ActionButton
											onClick={() =>
												onApprove(task.task_id)
											}
											icon={<IconPlayerPlay size={16} />}
											className="bg-green-600 text-white hover:bg-green-500"
										>
											Approve & Run
										</ActionButton>
									)}
									{task.status === "pending" &&
										task.assignee === "user" && (
											<ActionButton
												onClick={() =>
													onMarkComplete(task.task_id)
												}
												icon={
													<IconCircleCheck
														size={16}
													/>
												}
												className="bg-green-600 text-white hover:bg-green-500"
											>
												Mark as Complete
											</ActionButton>
										)}
									<ActionButton
										onClick={() =>
											onArchiveTask(task.task_id)
										}
										icon={<IconArchive size={16} />}
										className="bg-neutral-700 text-neutral-200 hover:bg-neutral-600"
									>
										Archive
									</ActionButton>
								</div>
							</>
						)}
					</footer>
				</>
			)}
		</aside>
	)
}

export default TaskDetailsPanel
