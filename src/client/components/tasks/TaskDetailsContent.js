"use client"

import React from "react"
import { cn } from "@utils/cn"
import { taskStatusColors, priorityMap } from "./constants"
import { IconBrain } from "@tabler/icons-react"

const TaskDetailsContent = ({ task }) => {
	if (!task) {
		return null
	}

	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default

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
		<div className="space-y-6">
			<div className="flex items-center gap-4 text-sm">
				<span className="text-sm text-neutral-400">Status:</span>
				<span
					className={cn(
						"font-semibold py-0.5 px-2 rounded-full text-xs",
						statusInfo.color,
						statusInfo.border.replace("border-", "bg-") + "/20"
					)}
				>
					{statusInfo.label}
				</span>
				<div className="w-px h-4 bg-[var(--color-primary-surface-elevated)]"></div>
				<span className="text-sm text-neutral-400">Priority:</span>
				<span className={cn("font-semibold", priorityInfo.color)}>
					{priorityInfo.label}
				</span>
			</div>
			{task.assignee === "ai" && task.plan && task.plan.length > 0 && (
				<div>
					<h4 className="text-lg font-semibold text-white mb-3">
						Plan
					</h4>
					<div className="space-y-2">
						{task.plan.map((step, index) => (
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
						))}
					</div>
				</div>
			)}
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
										task.progress_updates.length - 1 && (
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
										<Tooltip
											place="right-start"
											id="task-details-tooltip"
											style={{ zIndex: 9999 }}
										/>
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
							{mainContent && typeof mainContent === "string" && (
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
	)
}

export default TaskDetailsContent
