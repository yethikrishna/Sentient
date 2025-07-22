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
			className="fixed inset-0 bg-black/50 flex justify-center items-center z-50 p-4"
			onClick={onClose}
		>
			<Tooltip
				id="task-details-tooltip"
				place="right-start"
				style={{ zIndex: 99999 }}
			/>
			<motion.div
				initial={{ scale: 0.95, opacity: 0 }}
				animate={{ scale: 1, opacity: 1 }}
				exit={{ scale: 0.95, opacity: 0 }}
				transition={{ duration: 0.2 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-[var(--color-primary-background)] border border-[var(--color-primary-surface-elevated)] rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col"
			>

				<div className="flex justify-between items-start p-6 border-b border-[var(--color-primary-surface)]">
					<div className="flex-1 min-w-0">
						<h3 className="text-xl font-semibold text-[var(--color-text-primary)] truncate pr-4">
							{task.description}
						</h3>
					</div>
					<button
						onClick={onClose}
						className="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-primary-surface)] rounded-md transition-colors flex-shrink-0"
					>
						<IconX size={16} />
					</button>
				</div>

				<div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
					{/* Main Task Content & Original Outcome */}
					<div className="bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-lg p-4">
						<TaskDetailsContent task={task} />
					</div>

					{/* Follow-up Section for Changes, Clarifications, and Approvals */}
					{(chatHistory.length > 0 ||
						task.status === "clarification_pending" ||
						task.status === "approval_pending") && (
						<div className="bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-lg p-4 space-y-4">
							<h4 className="text-lg font-semibold text-[var(--color-text-primary)]">
								Conversation & Changes
							</h4>

							{/* Chat History */}
							<div className="space-y-3">
								{chatHistory.map((msg, index) => (
									<div
										key={index}
										className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
									>
										<div
											className={`p-3 rounded-lg max-w-[80%] ${
												msg.role === "user"
													? "bg-[var(--color-accent-blue)] text-white"
													: "bg-[var(--color-primary-surface-elevated)] text-[var(--color-text-primary)]"
											}`}
										>
											<p className="text-sm whitespace-pre-wrap">
												{msg.content}
											</p>
										</div>
									</div>
								))}
							</div>

							{/* Clarification Questions */}
							{task.status === "clarification_pending" && (
								<div className="bg-[var(--color-accent-orange)]/10 border border-[var(--color-accent-orange)]/20 rounded-lg p-4 space-y-4">
									<p className="font-medium text-[var(--color-text-primary)]">
										I need more information to proceed:
									</p>
									{latestRun.clarifying_questions.map((q) => (
										<div key={q.question_id} className="space-y-2">
											<label className="text-sm text-[var(--color-text-secondary)] block font-medium">
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
												rows={3}
												className="w-full p-3 bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-lg text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:border-[var(--color-accent-blue)] outline-none"
												placeholder="Your answer..."
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
											className="px-4 py-2 bg-[var(--color-accent-orange)] hover:bg-[var(--color-accent-orange)]/80 text-white rounded-lg font-medium transition-colors"
										>
											Submit Answers
										</button>
									</div>
								</div>
							)}

							{/* New Plan for Approval */}
							{task.status === "approval_pending" && (
								<div className="bg-[var(--color-accent-green)]/10 border border-[var(--color-accent-green)]/20 rounded-lg p-4 space-y-4">
									<p className="font-medium text-[var(--color-text-primary)] text-center">
										New plan requires your approval:
									</p>
									<div className="space-y-2">
										{(latestRun.plan || []).map((step, index) => (
											<div
												key={index}
												className="flex items-start gap-3 bg-[var(--color-primary-surface-elevated)] p-3 rounded-lg"
											>
												<div className="flex-shrink-0 w-6 h-6 bg-[var(--color-accent-blue)] rounded-full flex items-center justify-center text-white font-medium text-xs">
													{index + 1}
												</div>
												<div>
													<p className="font-medium text-[var(--color-text-primary)]">
														{step.tool}
													</p>
													<p className="text-sm text-[var(--color-text-secondary)] mt-1">
														{step.description}
													</p>
												</div>
											</div>
										))}
									</div>
									<div className="flex justify-center gap-3">
										<button
											onClick={() => {
												onApprove(task.task_id)
												onClose()
											}}
											disabled={missingTools.length > 0}
											className="px-4 py-2 bg-[var(--color-accent-green)] hover:bg-[var(--color-accent-green-hover)] text-white rounded-lg font-medium disabled:opacity-50 transition-colors"
										>
											Approve Plan
										</button>
										<button
											onClick={() => {
												onDelete(task.task_id)
												onClose()
											}}
											className="px-4 py-2 bg-[var(--color-accent-red)] hover:bg-[var(--color-accent-red-hover)] text-white rounded-lg font-medium transition-colors"
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
					<div className="bg-[var(--color-accent-orange)]/10 border border-[var(--color-accent-orange)]/20 rounded-lg p-4 m-6 flex items-center gap-3">
						<IconAlertTriangle className="text-[var(--color-accent-orange)]" size={20} />
						<p className="text-[var(--color-text-primary)] text-sm font-medium">
							This plan requires tools you haven't connected:{" "}
							<span className="font-semibold">{missingTools.join(", ")}</span>
						</p>
						<ConnectToolButton toolName="" />
					</div>
				)}

				{/* Footer with actions and chat input */}
				<div className="border-t border-[var(--color-primary-surface)] p-6">
					{task.status === "completed" ? (
						<div className="space-y-3">
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
										className="flex-grow p-3 bg-[var(--color-primary-surface)] border border-[var(--color-primary-surface-elevated)] rounded-lg text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] focus:border-[var(--color-accent-blue)] outline-none"
									/>
									<button
										onClick={handleSendChatMessage}
										className="p-3 bg-[var(--color-accent-blue)] hover:bg-[var(--color-accent-blue-hover)] text-white rounded-lg transition-colors"
									>
										<IconSend size={16} />
									</button>
								</div>
							)}
							<button
								onClick={() => {
									onArchiveTask(task.task_id)
									onClose()
								}}
								className="w-full py-3 text-sm bg-[var(--color-accent-green)]/20 text-[var(--color-accent-green)] border border-[var(--color-accent-green)]/30 rounded-lg hover:bg-[var(--color-accent-green)]/30 transition-colors flex items-center justify-center gap-2 font-medium"
							>
								<IconArchive size={16} /> Archive Task
							</button>
						</div>
					) : (
						<div className="flex justify-end gap-3">
							<button
								onClick={() => {
									onDelete(task.task_id)
									onClose()
								}}
								className="px-4 py-2 text-sm text-[var(--color-accent-red)] hover:bg-[var(--color-accent-red)]/10 rounded-lg transition-colors flex items-center gap-2"
							>
								<IconTrash size={16} /> Delete
							</button>
							<button
								onClick={() => onEdit(task)}
								className="px-4 py-2 text-sm text-[var(--color-accent-orange)] hover:bg-[var(--color-accent-orange)]/10 rounded-lg transition-colors flex items-center gap-2"
							>
								<IconPencil size={16} /> Edit
							</button>
							{task.assignee === "user" &&
								task.status === "pending" && (
									<button
										onClick={() => {
											onMarkComplete(task.task_id)
											onClose()
										}}
										className="px-4 py-2 text-sm bg-[var(--color-accent-green)] hover:bg-[var(--color-accent-green-hover)] text-white rounded-lg transition-colors flex items-center gap-2"
									>
										<IconCircleCheck size={16} /> Mark Complete
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
