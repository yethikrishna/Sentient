// A new file: src/client/components/tasks/TaskDetailsModal.js
"use client"

import React from "react"
import { motion } from "framer-motion"
import {
	IconX,
	IconClock,
	IconPlayerPlay,
	IconCircleCheck,
	IconMailQuestion,
	IconAlertCircle,
	IconHelpCircle,
	IconRefresh,
	IconBrain
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import { Tooltip } from "react-tooltip"

const statusMap = {
	planning: { icon: IconRefresh, color: "text-blue-400", label: "Planning" },
	pending: { icon: IconClock, color: "text-yellow-400", label: "Pending" },
	processing: {
		icon: IconPlayerPlay,
		color: "text-blue-400",
		label: "Processing"
	},
	completed: {
		icon: IconCircleCheck,
		color: "text-green-400",
		label: "Completed"
	},
	error: { icon: IconAlertCircle, color: "text-red-400", label: "Error" },
	approval_pending: {
		icon: IconMailQuestion,
		color: "text-purple-400",
		label: "Approval Pending"
	},
	active: { icon: IconRefresh, color: "text-green-400", label: "Active" },
	clarification_pending: {
		icon: IconHelpCircle,
		color: "text-orange-400",
		label: "Needs Clarification"
	},
	cancelled: { icon: IconX, color: "text-gray-500", label: "Cancelled" },
	default: { icon: IconHelpCircle, color: "text-gray-400", label: "Unknown" }
}

const priorityMap = {
	0: { label: "High", color: "text-red-400" },
	1: { label: "Medium", color: "text-yellow-400" },
	2: { label: "Low", color: "text-green-400" },
	default: { label: "Unknown", color: "text-gray-400" }
}

const TaskDetailsModal = ({ task, onClose, onApprove, integrations = [] }) => {
	const statusInfo = statusMap[task.status] || statusMap.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default

	let missingTools = []
	if (task.status === "approval_pending") {
		const requiredTools = new Set(task.plan?.map((step) => step.tool) || [])
		requiredTools.forEach((toolName) => {
			if (
				!integrations.find((i) => i.name === toolName)?.connected &&
				integrations.find((i) => i.name === toolName)?.auth_type !==
					"builtin"
			) {
				missingTools.push(
					integrations.find((i) => i.name === toolName)
						?.display_name || toolName
				)
			}
		})
	}

	const { thoughts, finalAnswer, mainContent } =
		task.result && typeof task.result === "string"
			? {
					thoughts: task.result.match(
						/<think>([\s\S]*?)<\/think>/
					)?.[1],
					finalAnswer: task.result.match(
						/<final_answer>([\s\S]*?)<\/final_answer>/
					)?.[1],
					mainContent: task.result
						.replace(/<think>[\s\S]*?<\/think>/g, "")
						.replace(/<final_answer>[\s\S]*?<\/final_answer>/g, "")
				}
			: { thoughts: null, finalAnswer: null, mainContent: task.result }

	return (
		<motion.div
			initial={{ opacity: 0 }}
			animate={{ opacity: 1 }}
			exit={{ opacity: 0 }}
			className="fixed inset-0 bg-black/60 backdrop-blur-sm flex justify-center items-center z-50 p-4"
			onClick={onClose}
		>
			<Tooltip id="task-details-tooltip" />
			<motion.div
				initial={{ scale: 0.9, y: 20 }}
				animate={{ scale: 1, y: 0 }}
				exit={{ scale: 0.9, y: 20 }}
				onClick={(e) => e.stopPropagation()}
				className="bg-gradient-to-br from-[var(--color-primary-surface)] to-[var(--color-primary-background)] p-6 rounded-2xl shadow-xl w-full max-w-3xl border border-[var(--color-primary-surface-elevated)] max-h-[90vh] flex flex-col"
			>
				<div className="flex justify-between items-center mb-6">
					<h3 className="text-2xl font-semibold text-white truncate">
						{task.description}
					</h3>
					<button onClick={onClose} className="hover:text-white">
						<IconX />
					</button>
				</div>
				<div className="overflow-y-auto custom-scrollbar pr-2 space-y-6">
					<div className="flex items-center gap-4 text-sm">
						<span className="text-[var(--color-text-secondary)]">
							Status:
						</span>
						<span
							className={cn(
								"font-semibold py-0.5 px-2 rounded-full text-xs",
								statusInfo.color,
								statusInfo.color.replace("text-", "bg-") + "/20"
							)}
						>
							{statusInfo.label}
						</span>
						<div className="w-px h-4 bg-[var(--color-primary-surface-elevated)]"></div>
						<span className="text-[var(--color-text-secondary)]">
							Priority:
						</span>
						<span
							className={cn("font-semibold", priorityInfo.color)}
						>
							{priorityInfo.label}
						</span>
					</div>
					<div>
						<h4 className="text-lg font-semibold text-white mb-3">
							Plan
						</h4>
						<div className="space-y-2">
							{task.plan && task.plan.length > 0 ? (
								task.plan.map((step, index) => (
									<div
										key={index}
										className="flex items-start gap-3 bg-[var(--color-primary-surface)]/70 p-3 rounded-md"
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
								))
							) : (
								<p className="text-sm text-[var(--color-text-secondary)] italic">
									No plan has been generated yet.
								</p>
							)}
						</div>
					</div>
					{task.progress_updates?.length > 0 && (
						<div>
							<h4 className="text-lg font-semibold text-white mb-4">
								Progress
							</h4>
							<div className="space-y-4">
								{task.progress_updates.map((update, index) => (
									<div key={index} className="flex gap-4">
										<div className="flex flex-col items-center">
											<div className="w-4 h-4 bg-blue-500 rounded-full border-2 border-neutral-800"></div>
											{index <
												task.progress_updates.length -
													1 && (
												<div className="w-0.5 flex-grow bg-[var(--color-primary-surface-elevated)]"></div>
											)}
										</div>
										<div>
											<p className="text-sm text-white -mt-1">
												{update.message}
											</p>
											<p className="text-xs text-[var(--color-text-muted)] mt-1.5">
												{new Date(
													update.timestamp
												).toLocaleString()}
											</p>
										</div>
									</div>
								))}
							</div>
						</div>
					)}
					{(task.result || task.error) && (
						<div className="pt-4 border-t border-[var(--color-primary-surface-elevated)]">
							<h4 className="text-lg font-semibold text-white mb-4">
								Outcome
							</h4>
							{task.error ? (
								<pre className="text-sm bg-red-900/30 p-4 rounded-md text-red-300 whitespace-pre-wrap font-mono border border-[var(--color-accent-red)]/50">
									{task.error}
								</pre>
							) : (
								<div className="space-y-4 text-gray-300">
									{thoughts && (
										<details className="bg-[var(--color-primary-surface)]/50 rounded-lg p-3 border border-[var(--color-primary-surface-elevated)]">
											<summary
												className="cursor-pointer text-sm text-[var(--color-text-secondary)] font-semibold hover:text-white flex items-center gap-2"
												data-tooltip-id="task-details-tooltip"
												data-tooltip-content="See the step-by-step reasoning the agent used to produce the result."
											>
												<IconBrain
													size={16}
													className="text-yellow-400"
												/>{" "}
												View Agent's Thoughts
											</summary>
											<pre className="mt-3 text-xs text-gray-400 whitespace-pre-wrap font-mono">
												{thoughts}
											</pre>
										</details>
									)}
									{mainContent &&
										typeof mainContent === "string" && (
											<div
												dangerouslySetInnerHTML={{
													__html: mainContent.replace(
														/\n/g,
														"<br />"
													)
												}}
											/>
										)}
									{finalAnswer && (
										<div className="mt-2 p-4 bg-green-900/30 border border-[var(--color-accent-green)]/50 rounded-lg">
											<p className="text-sm font-semibold text-green-300 mb-2">
												Final Answer
											</p>
											<div
												dangerouslySetInnerHTML={{
													__html: finalAnswer.replace(
														/\n/g,
														"<br />"
													)
												}}
											/>
										</div>
									)}
								</div>
							)}
						</div>
					)}
				</div>
				<div className="flex justify-end mt-6 pt-4 border-t border-[var(--color-primary-surface-elevated)] gap-4">
					<button
						onClick={onClose}
						className="py-2.5 px-6 rounded-lg bg-[var(--color-primary-surface-elevated)] hover:bg-[var(--color-primary-surface)] text-sm transition-colors"
					>
						Close
					</button>
					{task.status === "approval_pending" && (
						<button
							onClick={() => onApprove(task.task_id)}
							className="py-2.5 px-6 rounded-lg bg-[var(--color-accent-green)] hover:bg-[var(--color-accent-green-hover)] text-sm flex items-center gap-2 disabled:opacity-50 transition-colors"
							disabled={missingTools.length > 0}
						>
							<IconCircleCheck className="w-5 h-5" />
							Approve Plan
						</button>
					)}
				</div>
			</motion.div>
		</motion.div>
	)
}

export default TaskDetailsModal
