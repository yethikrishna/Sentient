"use client"

import React from "react"
import { format, parseISO } from "date-fns"
import { taskStatusColors, priorityMap } from "./constants"
import { cn } from "@utils/cn"
import CollapsibleSection from "./CollapsibleSection"
import ExecutionUpdate from "./ExecutionUpdate"
import ReactMarkdown from "react-markdown"

const RecurringTaskDetails = ({ task, onAnswerClarifications }) => {
	if (!task) return null

	const statusInfo = taskStatusColors[task.status] || taskStatusColors.default
	const priorityInfo = priorityMap[task.priority] || priorityMap.default
	const schedule = task.schedule || {}
	const scheduleText =
		schedule.frequency === "daily"
			? `Recurring: Daily at ${schedule.time}`
			: `Recurring: Weekly on ${schedule.days?.join(", ") || "selected days"} at ${schedule.time}`

	return (
		<div className="space-y-6">
			{/* Meta Info */}
			<div>
				<label className="text-sm font-medium text-neutral-400 block mb-2">
					Meta
				</label>
				<div className="flex items-center gap-4 text-sm bg-neutral-800/50 p-3 rounded-lg">
					<span className="text-sm text-neutral-400">Status:</span>
					<span
						className={cn(
							"font-semibold py-0.5 px-2 rounded-full text-xs flex items-center gap-1",
							statusInfo.color,
							statusInfo.border.replace("border-", "bg-") + "/20"
						)}
					>
						<statusInfo.icon size={12} />
						{statusInfo.label}
					</span>
					<div className="w-px h-4 bg-neutral-700"></div>
					<span className="text-sm text-neutral-400">Priority:</span>
					<span className={cn("font-semibold", priorityInfo.color)}>
						{priorityInfo.label}
					</span>
				</div>
			</div>

			{/* --- Researched Context (if planning) --- */}
			{task.status === "planning" && task.found_context && (
				<div>
					<label className="text-sm font-medium text-neutral-400 block mb-2">
						Researched Context
					</label>
					<div className="bg-neutral-800/50 p-3 rounded-lg text-sm text-neutral-300 whitespace-pre-wrap border border-neutral-700/50">
						<ReactMarkdown className="prose prose-sm prose-invert">
							{task.found_context}
						</ReactMarkdown>
					</div>
				</div>
			)}

			{/* Schedule */}
			<div>
				<label className="text-sm font-medium text-neutral-400 block mb-2">
					Schedule
				</label>
				<div className="bg-neutral-800/50 p-3 rounded-lg text-sm">
					{scheduleText}
				</div>
			</div>

			{/* Plan */}
			{task.plan && task.plan.length > 0 && (
				<div>
					<h4 className="font-semibold text-neutral-300 mb-2">
						Plan
					</h4>
					<div className="space-y-2">
						{task.plan.map((step, index) => (
							<div
								key={index}
								className="flex items-start gap-3 p-3 bg-neutral-800/50 rounded-lg border border-neutral-700/50"
							>
								<div className="flex-shrink-0 w-5 h-5 bg-neutral-700 rounded-full flex items-center justify-center text-xs font-bold">
									{index + 1}
								</div>
								<div>
									<p className="text-sm font-medium text-neutral-100">
										{step.tool}
									</p>
									<p className="text-sm text-neutral-400">
										{step.description}
									</p>
								</div>
							</div>
						))}
					</div>
				</div>
			)}

			{/* Run History */}
			{task.runs && task.runs.length > 0 && (
				<div>
					<h4 className="font-semibold text-neutral-300 mb-2">
						Run History
					</h4>
					<div className="space-y-3">
						{task.runs
							.slice()
							.reverse()
							.map((run, index) => {
								const runNumber = task.runs.length - index
								const runStatusInfo =
									taskStatusColors[run.status] ||
									taskStatusColors.default
								const runDate = run.execution_start_time
									? parseISO(run.execution_start_time)
									: null
								const title = (
									<div className="flex flex-col gap-1 w-full">
										<div className="flex items-center justify-between w-full">
											<div className="flex items-center gap-2">
												<span className="font-semibold text-neutral-200 text-sm">
													Run #{runNumber}
												</span>
											</div>
											<span
												className={cn(
													"font-semibold text-xs flex items-center gap-1.5 py-0.5 px-2 rounded-full",
													runStatusInfo.color,
													runStatusInfo.border.replace(
														"border-",
														"bg-"
													) + "/20"
												)}
											>
												<runStatusInfo.icon size={12} />
												{runStatusInfo.label}
											</span>
										</div>
										<div className="text-xs text-neutral-400">
											{runDate
												? format(
														runDate,
														"MMMM d, yyyy 'at' p"
													)
												: "Run pending..."}
										</div>
									</div>
								)
								return (
									<CollapsibleSection
										key={run.run_id}
										title={title}
										defaultOpen={index === 0}
									>
										<div className="bg-neutral-800/50 p-4 rounded-lg border border-neutral-700/50 space-y-4 mt-2">
											{run.plan &&
												run.plan.length > 0 && (
													<div>
														<h4 className="font-semibold text-neutral-300 mb-2">
															Plan
														</h4>
														<div className="space-y-2">
															{run.plan.map(
																(
																	step,
																	index
																) => (
																	<div
																		key={
																			index
																		}
																		className="flex items-start gap-3 p-3 bg-neutral-900/50 rounded-lg border border-neutral-700/50"
																	>
																		<div className="flex-shrink-0 w-5 h-5 bg-neutral-700 rounded-full flex items-center justify-center text-xs font-bold">
																			{index +
																				1}
																		</div>
																		<div>
																			<p className="text-sm font-medium text-neutral-100">
																				{
																					step.tool
																				}
																			</p>
																			<p className="text-sm text-neutral-400">
																				{
																					step.description
																				}
																			</p>
																		</div>
																	</div>
																)
															)}
														</div>
													</div>
												)}

											{run.progress_updates &&
											run.progress_updates.length > 0 ? (
												run.progress_updates.map(
													(update, index) => (
														<ExecutionUpdate
															key={index}
															update={update}
														/>
													)
												)
											) : (
												<p className="text-sm text-neutral-500">
													No execution log for this
													run.
												</p>
											)}
										</div>
									</CollapsibleSection>
								)
							})}
					</div>
				</div>
			)}
		</div>
	)
}

export default RecurringTaskDetails
