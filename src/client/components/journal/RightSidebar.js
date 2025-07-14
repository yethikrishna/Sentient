"use client"

import React, { useState, useMemo } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { cn } from "@utils/cn"
import {
	IconCalendar,
	IconChecklist,
	IconMessageQuestion,
	IconRefresh,
	IconHelpCircle,
	IconExternalLink
} from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"
import RightSideCalendar from "./RightSideCalendar"
import WorkflowCard from "./WorkflowCard"
import ClarificationCard from "./ClarificationCard"
import CollapsibleSection from "./CollapsibleSection"
import SidebarTabButton from "./SidebarTabButton"

const RightSidebar = ({
	isOpen,
	setIsOpen,
	activeTab,
	setActiveTab,
	viewDate,
	setViewDate,
	journalEntriesByDate,
	recurringTasksByDate,
	allTasks,
	integrations,
	onEditTask,
	onDeleteTask,
	onApproveTask,
	onViewTask,
	onUpdateSchedule,
	onToggleEnableTask,
	onAnswerClarifications
}) => {
	const router = useRouter()

	// eslint-disable-line
	const [openSections, setOpenSections] = useState({
		active: true,
		approval_pending: true,
		processing: true,
		completed: true
	})

	const recurringTasks = useMemo(
		() => allTasks.filter((t) => t.schedule?.type === "recurring"),
		[allTasks]
	)

	const clarificationTasks = useMemo(
		() => allTasks.filter((t) => t.status === "clarification_pending"),
		[allTasks]
	)

	const groupedTasks = useMemo(
		() => ({
			active: allTasks.filter((t) => t.status === "active"),
			approval_pending: allTasks.filter(
				(t) => t.status === "approval_pending"
			),
			processing: allTasks.filter((t) =>
				["processing", "pending"].includes(t.status)
			),
			completed: allTasks.filter((t) =>
				["completed", "error", "cancelled"].includes(t.status)
			)
		}),
		[allTasks]
	)

	const toggleSection = (section) =>
		setOpenSections((p) => ({ ...p, [section]: !p[section] }))

	const handleTabClick = (tabName) => {
		if (!isOpen || activeTab !== tabName) {
			setActiveTab(tabName)
			setIsOpen(true)
		} else {
			setIsOpen(false)
		}
	}

	return (
		<motion.aside
			animate={{ width: isOpen ? 400 : 50 }}
			transition={{ type: "spring", stiffness: 400, damping: 30 }}
			className="hidden md:flex flex-col h-screen shrink-0 relative"
		>
			<div className="flex h-full">
				<Tooltip id="sidebar-tooltip" place="left" />
				<div className="flex-1 overflow-y-auto custom-scrollbar bg-[var(--color-primary-surface)]/50 backdrop-blur-lg">
					{activeTab === "calendar" && (
						<div className="p-4">
							<RightSideCalendar
								viewDate={viewDate}
								onDateChange={setViewDate}
								entriesByDate={journalEntriesByDate}
								recurringTasksByDate={recurringTasksByDate}
							/>
						</div>
					)}
					{activeTab === "workflows" && (
						<div className="space-y-4 p-4">
							<div className="flex justify-between items-center gap-2 mb-4">
								<div className="flex items-center gap-2">
									<h2 className="text-xl font-semibold">
										Workflows
									</h2>
									<button
										data-tooltip-id="journal-help"
										data-tooltip-content="Recurring tasks (workflows) appear here. Manage them from the Tasks page."
										className="text-neutral-500 hover:text-white"
									>
										<IconHelpCircle size={16} />
									</button>
								</div>
								<button
									onClick={() => router.push("/tasks")}
									className="flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 transition-colors"
									data-tooltip-id="sidebar-tooltip"
									data-tooltip-content="Go to full tasks page"
								>
									<IconExternalLink size={16} />
									<span>View All</span>
								</button>
							</div>
							<div className="space-y-2">
								{recurringTasks.length > 0 ? (
									recurringTasks.map((task) => (
										<WorkflowCard
											key={task.task_id}
											task={task}
											onToggleEnable={onToggleEnableTask}
											onDeleteTask={onDeleteTask}
										/>
									))
								) : (
									<p className="text-center text-gray-500 py-10">
										No recurring workflows found.
									</p>
								)}
							</div>
						</div>
					)}
					{activeTab === "clarifications" && (
						<div className="space-y-4 p-4">
							<div className="flex justify-center items-center gap-2 mb-4">
								<h2 className="text-xl font-semibold">
									Needs Your Input
								</h2>
								<button
									data-tooltip-id="journal-help"
									data-tooltip-content="Sometimes Sentient needs more information to create a plan. Your answers will appear here."
									className="text-neutral-500 hover:text-white"
								>
									<IconHelpCircle size={16} />
								</button>
							</div>
							{clarificationTasks.length > 0 ? (
								clarificationTasks.map((task) => (
									<ClarificationCard
										key={task.task_id}
										task={task}
										onSubmitAnswers={onAnswerClarifications}
									/>
								))
							) : (
								<p className="text-center text-gray-500 py-10">
									All clear! No questions waiting.
								</p>
							)}
						</div>
					)}
					{activeTab === "tasks" && (
						<div className="space-y-4 p-4">
							<div className="flex justify-between items-center mb-4">
								<h2 className="text-xl font-semibold">
									Tasks Overview
								</h2>
								<button
									onClick={() => router.push("/tasks")}
									className="flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 transition-colors"
									data-tooltip-id="sidebar-tooltip"
									data-tooltip-content="Go to full tasks page"
								>
									<IconExternalLink size={16} />
									<span>View All</span>
								</button>
							</div>
							<CollapsibleSection
								title="Active"
								tasks={groupedTasks.active}
								isOpen={openSections.active}
								toggleOpen={() => toggleSection("active")}
								onEditTask={onEditTask}
								onDeleteTask={onDeleteTask}
								onViewDetails={onViewTask}
							/>
							<CollapsibleSection
								title="Pending Approval"
								tasks={groupedTasks.approval_pending}
								isOpen={openSections.approval_pending}
								toggleOpen={() =>
									toggleSection("approval_pending")
								}
								integrations={integrations}
								onEditTask={onEditTask}
								onDeleteTask={onDeleteTask}
								onApproveTask={onApproveTask}
								onViewDetails={onViewTask}
							/>
							<CollapsibleSection
								title="Processing"
								tasks={groupedTasks.processing}
								isOpen={openSections.processing}
								toggleOpen={() => toggleSection("processing")}
								onEditTask={onEditTask}
								onDeleteTask={onDeleteTask}
								onViewDetails={onViewTask}
							/>
							<CollapsibleSection
								title="Completed"
								tasks={groupedTasks.completed}
								isOpen={openSections.completed}
								toggleOpen={() => toggleSection("completed")}
								onEditTask={onEditTask}
								onDeleteTask={onDeleteTask}
								onViewDetails={onViewTask}
							/>
						</div>
					)}
				</div>

				<div className="w-[50px] h-full flex flex-col items-center justify-start gap-4 bg-[var(--color-primary-surface)] border-l border-[var(--color-primary-surface-elevated)] pt-6">
					<SidebarTabButton
						label="Calendar"
						icon={<IconCalendar size={22} />}
						tooltipContent="View your calendar and daily entries."
						isActive={isOpen && activeTab === "calendar"}
						onClick={() => handleTabClick("calendar")}
					/>
					<SidebarTabButton
						label="Tasks"
						icon={<IconChecklist size={22} />}
						tooltipContent="Get a quick overview of all your tasks."
						isActive={isOpen && activeTab === "tasks"}
						onClick={() => handleTabClick("tasks")}
					/>
					<SidebarTabButton
						label="Clarifications"
						icon={<IconMessageQuestion size={22} />}
						tooltipContent="Answer questions Sentient has about your tasks."
						isActive={isOpen && activeTab === "clarifications"}
						onClick={() => handleTabClick("clarifications")}
					/>
					<SidebarTabButton
						label="Workflows"
						icon={<IconRefresh size={22} />}
						tooltipContent="See your active recurring tasks (workflows)."
						isActive={isOpen && activeTab === "workflows"}
						onClick={() => handleTabClick("workflows")}
					/>
				</div>
			</div>
		</motion.aside>
	)
}

export default RightSidebar
