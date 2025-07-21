// A new file: src/client/components/tasks/TaskDetailsModal.js
"use client"

import React, { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import toast from "react-hot-toast"
import { motion } from "framer-motion"
import {
	IconX,
	IconTrash,
	IconPencil,
	IconCircleCheck,
	IconAlertTriangle,
	IconSend,
	IconArchive
} from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"
import TaskDetailsContent from "./TaskDetailsContent"
import ConnectToolButton from "./ConnectToolButton"

const TaskDetailsModal = ({
	task,
	onClose,
	onEdit,
	onApprove,
	onDelete,
	integrations = [],
	onAnswerClarifications,
	onArchiveTask,
	onMarkComplete,
	onUpdateTask // This prop is still passed but its usage for archiving is changed.
}) => {
	const [chatInput, setChatInput] = useState("")
	const [chatHistory, setChatHistory] = useState(task.chat_history || [])
	const [clarificationAnswers, setClarificationAnswers] = useState({})
	const router = useRouter()
	const chatEndRef = useRef(null)
	useEffect(() => {
		chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
	}, [chatHistory])

	const runs = task.runs || []
	const latestRun = runs.length > 0 ? runs[runs.length - 1] : {}

	let missingTools = []
	if (task.status === "approval_pending") {
		const requiredTools = new Set(
			latestRun.plan?.map((step) => step.tool) || []
		)
		requiredTools.forEach((toolName) => {
			const integration = integrations.find((i) => i.name === toolName)
			if (
				integration &&
				!integration.connected &&
				integration.auth_type !== "builtin"
			) {
				missingTools.push(integration.display_name || toolName)
			}
		})
	}

	const handleSendChatMessage = async () => {
		if (!chatInput.trim()) return
		const newHumanMessage = {
			role: "user",
			content: chatInput,
			timestamp: new Date().toISOString()
		}
		setChatHistory((prev) => [...prev, newHumanMessage])
		const currentInput = chatInput
		setChatInput("")
		try {
			const response = await fetch("/api/tasks/chat", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					taskId: task.task_id,
					message: currentInput
				})
			})
			const data = await response.json()
			if (!response.ok)
				throw new Error(data.error || "Failed to send message.")
			// We expect the backend to eventually stream back the AI response and update the task.
			// For now, we just close the modal and let the main page refresh.
			toast.success("Change request sent. The AI is working on it.")
			onClose()
		} catch (error) {
			toast.error(error.message)
			setChatHistory((prev) => prev.slice(0, -1)) // Revert optimistic update on error
		}
	}

	const handleAnswerChange = (questionId, text) => {
		setClarificationAnswers((prev) => ({ ...prev, [questionId]: text }))
	}

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
			onClick={onClose}
		>
			<Tooltip
				id="task-details-tooltip"
				place="right-start"
				style={{ zIndex: 99999 }}
			/>
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-dark-surface p-6 rounded-2xl shadow-xl w-full max-w-3xl border border-dark-surface-elevated max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-start mb-6">
					<div className="flex-1 min-w-0">
						<h3 className="text-2xl font-semibold text-white truncate pr-4">
							{task.description}
						</h3>
					</div>
					<button
						onClick={onClose}
						className="p-1 rounded-full hover:bg-dark-surface-elevated flex-shrink-0"
					>
						<IconX size={20} />
					</button>
				</div>

				<div className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-6">
					{/* Main Task Content & Original Outcome */}
					<TaskDetailsContent task={task} />

					{/* Follow-up Section for Changes, Clarifications, and Approvals */}
					{(chatHistory.length > 0 ||
						task.status === "clarification_pending" ||
						task.status === "approval_pending") && (
						<div className="pt-6 mt-6 border-t border-dark-surface-elevated space-y-4">
							<h4 className="text-lg font-semibold text-white">
								Conversation & Changes
							</h4>

							{/* Chat History */}
							{chatHistory.map((msg, index) => (
								<div
									key={index}
									className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
								>
									<div
										className={`p-3 rounded-lg max-w-[80%] ${msg.role === "user" ? "bg-sentient-blue" : "bg-neutral-700"}`}
									>
										<p className="text-sm whitespace-pre-wrap">
											{msg.content}
										</p>
									</div>
								</div>
							))}

							{/* Clarification Questions */}
							{task.status === "clarification_pending" && (
								<div className="bg-neutral-700/50 p-4 rounded-lg space-y-3">
									<p className="text-sm font-semibold">
										I need more information to proceed:
									</p>
									{latestRun.clarifying_questions.map((q) => (
										<div key={q.question_id}>
											<label className="text-xs text-neutral-400 block mb-1">
												{q.text}
											</label>
											<textarea
												value={
													clarificationAnswers[
														q.question_id
													] || ""
												}
												onChange={(e) =>
													handleAnswerChange(
														q.question_id,
														e.target.value
													)
												}
												rows={2}
												className="w-full p-2 bg-dark-bg border border-dark-surface-elevated rounded-md text-sm"
											/>
										</div>
									))}
									<div className="flex justify-end">
										<button
											onClick={() => {
												onAnswerClarifications(
													task.task_id,
													Object.entries(
														clarificationAnswers
													).map(([qid, atext]) => ({
														question_id: qid,
														answer_text: atext
													}))
												)
												onClose()
											}}
											className="px-4 py-2 text-sm bg-sentient-blue rounded-lg hover:bg-sentient-blue-dark"
										>
											Submit Answers
										</button>
									</div>
								</div>
							)}

							{/* New Plan for Approval */}
							{task.status === "approval_pending" && (
								<div className="bg-neutral-700/50 p-4 rounded-lg space-y-4">
									<p className="text-sm font-semibold text-center">
										New plan requires your approval:
									</p>
									<div className="space-y-2">
										{(latestRun.plan || []).map(
											(step, index) => (
												<div
													key={index}
													className="flex items-start gap-3 bg-dark-surface/70 p-3 rounded-md border border-dark-surface-elevated"
												>
													<div className="flex-shrink-0 text-[var(--color-accent-blue)] font-bold mt-0.5">
														{index + 1}.
													</div>
													<div>
														<p className="font-semibold text-white">
															{step.tool}
														</p>
														<p className="text-sm text-[var(--color-text-secondary)]">
															{step.description}
														</p>
													</div>
												</div>
											)
										)}
									</div>
									<div className="flex justify-center gap-3">
										<button
											onClick={() => {
												onApprove(task.task_id)
												onClose()
											}}
											disabled={missingTools.length > 0}
											className="px-4 py-2 text-sm bg-green-500/20 text-green-300 rounded-lg hover:bg-green-500/40 disabled:opacity-50"
										>
											Approve Plan
										</button>
										<button
											onClick={() => {
												onDelete(task.task_id)
												onClose()
											}}
											className="px-4 py-2 text-sm bg-red-500/20 text-red-300 rounded-lg hover:bg-red-500/40"
										>
											Disapprove
										</button>
									</div>
								</div>
							)}
						</div>
					)}
					<div ref={chatEndRef} />
				</div>

				{missingTools.length > 0 && (
					<div className="bg-yellow-900/50 border border-yellow-500/50 p-3 rounded-lg flex items-center gap-3 mt-4">
						<IconAlertTriangle className="text-yellow-400" />
						<p className="text-yellow-300 text-sm">
							This plan requires tools you haven't connected:{" "}
							<b>{missingTools.join(", ")}</b>.
						</p>
						<ConnectToolButton toolName="" />
					</div>
				)}

				{/* Footer with actions and chat input */}
				<div className="mt-6 pt-4 border-t border-dark-surface-elevated">
					{task.status === "completed" ? (
						<div className="flex flex-col gap-3">
							{task.assignee === "ai" && (
								<div className="flex items-center gap-3">
									<input
										type="text"
										value={chatInput}
										onChange={(e) =>
											setChatInput(e.target.value)
										}
										onKeyDown={(e) =>
											e.key === "Enter" &&
											handleSendChatMessage()
										}
										placeholder="Need changes? Chat with the AI..."
										className="flex-grow p-2 bg-neutral-800/50 border border-neutral-700 rounded-lg"
									/>
									<button
										onClick={handleSendChatMessage}
										className="p-2 bg-sentient-blue rounded-lg hover:bg-sentient-blue-dark transition-colors"
									>
										<IconSend size={18} />
									</button>
								</div>
							)}
							<button
								onClick={() => {
									onArchiveTask(task.task_id)
									onClose()
								}}
								className="w-full text-center py-2 text-sm bg-green-500/20 text-green-300 rounded-lg hover:bg-green-500/40 flex items-center justify-center gap-2"
							>
								<IconArchive size={16} /> Archive Task
							</button>
						</div>
					) : (
						<div className="flex justify-end gap-2">
							<button
								onClick={() => {
									onDelete(task.task_id)
									onClose()
								}}
								className="py-2 px-4 text-sm rounded-lg hover:bg-red-500/20 text-red-300"
							>
								<IconTrash size={16} />
							</button>
							<button
								onClick={() => onEdit(task)}
								className="py-2 px-4 text-sm rounded-lg hover:bg-orange-500/20 text-orange-400"
							>
								<IconPencil size={16} />
							</button>
							{task.assignee === "user" &&
								task.status === "pending" && (
									<button
										onClick={() => {
											onMarkComplete(task.task_id)
											onClose()
										}}
										className="py-2 px-4 text-sm rounded-lg bg-green-500/20 text-green-300 hover:bg-green-500/40 flex items-center gap-2"
									>
										<IconCircleCheck size={16} /> Mark
										Complete
									</button>
								)}
						</div>
					)}
				</div>
			</motion.div>
		</motion.div>
	)
}

export default TaskDetailsModal
