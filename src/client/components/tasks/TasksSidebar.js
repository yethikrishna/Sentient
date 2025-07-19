"use client"

import React, { useMemo } from "react"
import { motion } from "framer-motion"
import {
	IconCalendar,
	IconMessageQuestion,
	IconHelpCircle
} from "@tabler/icons-react"
import { Tooltip } from "react-tooltip"
import RightSideCalendar from "./RightSideCalendar"
import ClarificationCard from "./ClarificationCard"
import SidebarTabButton from "./SidebarTabButton"

const TasksSidebar = ({
	isOpen,
	setIsOpen,
	activeTab,
	setActiveTab,
	viewDate,
	setViewDate,
	allTasks,
	tasksByDate,
	onAnswerClarifications
}) => {
	// eslint-disable-line

	const clarificationTasks = useMemo(
		() => allTasks.filter((t) => t.status === "clarification_pending"),
		[allTasks]
	)

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
				<Tooltip
					id="sidebar-tooltip"
					place="right-start"
					style={{ zIndex: 9999 }}
				/>
				<div className="flex-1 overflow-y-auto custom-scrollbar bg-[var(--color-primary-surface)]/50 backdrop-blur-lg">
					{activeTab === "calendar" && (
						<div className="p-4">
							<RightSideCalendar
								viewDate={viewDate}
								onDateChange={setViewDate}
								itemsByDate={tasksByDate}
							/>
						</div>
					)}
					{activeTab === "clarifications" && (
						<div className="space-y-4 p-4">
							<div className="flex justify-center items-center gap-2 mb-4">
								<h2 className="text-xl font-semibold text-white">
									Needs Your Input
								</h2>
								<button
									data-tooltip-id="tasks-help"
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
				</div>

				<div className="w-[50px] h-full flex flex-col items-center justify-start gap-4 bg-[var(--color-primary-surface)] border-l border-[var(--color-primary-surface-elevated)] pt-6">
					<SidebarTabButton
						label="Calendar"
						icon={<IconCalendar size={22} />}
						tooltipContent="View your calendar and tasks."
						isActive={isOpen && activeTab === "calendar"}
						onClick={() => handleTabClick("calendar")}
					/>
					<SidebarTabButton
						label="Clarifications"
						icon={<IconMessageQuestion size={22} />}
						tooltipContent="Answer questions Sentient has about your tasks."
						isActive={isOpen && activeTab === "clarifications"}
						onClick={() => handleTabClick("clarifications")}
					/>
				</div>
			</div>
		</motion.aside>
	)
}

export default TasksSidebar
