"use client"

import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
	IconLayoutSidebarRightCollapse,
	IconLayoutSidebarRightExpand,
	IconMailQuestion,
	IconMessageQuestion
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import ApprovalCard from "./ApprovalCard"
import ClarificationCard from "./ClarificationCard"

const ActionSidebar = ({
	approvalTasks = [],
	clarificationTasks = [],
	...handlers
}) => {
	const [isOpen, setIsOpen] = useState(false)
	const [activeTab, setActiveTab] = useState("approval")

	const handleTabClick = (tab) => {
		setActiveTab(tab)
		if (!isOpen) {
			setIsOpen(true)
		}
	}

	const SidebarIcon = ({ icon, tabName, badgeCount, tooltipContent }) => (
		<div className="relative">
			<button
				onClick={() => handleTabClick(tabName)}
				className={cn(
					"p-3 rounded-lg transition-colors w-full",
					isOpen && activeTab === tabName
						? "bg-sentient-blue text-white"
						: "text-neutral-400 hover:bg-dark-surface-elevated hover:text-white"
				)}
				data-tooltip-id="tasks-tooltip"
				data-tooltip-content={tooltipContent}
				data-tooltip-place="left"
			>
				{icon}
			</button>
			{badgeCount > 0 && (
				<span className="absolute top-0 right-0 block h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-dark-surface" />
			)}
		</div>
	)

	return (
		<motion.aside
			initial={false}
			animate={{ width: isOpen ? 350 : 60 }}
			transition={{ type: "spring", stiffness: 400, damping: 40 }}
			className="hidden md:flex flex-col h-full bg-dark-surface shrink-0 border-l border-dark-surface-elevated"
		>
			<div className="flex h-full">
				{/* Icon Bar */}
				<div className="w-[60px] h-full flex flex-col items-center p-2 gap-2 border-r border-dark-surface-elevated">
					<button
						onClick={() => setIsOpen(!isOpen)}
						className="p-3 rounded-lg text-neutral-400 hover:bg-dark-surface-elevated hover:text-white"
						data-tooltip-id="tasks-tooltip"
						data-tooltip-content={
							isOpen ? "Collapse Sidebar" : "Expand Sidebar"
						}
						data-tooltip-place="left"
					>
						{isOpen ? (
							<IconLayoutSidebarRightCollapse size={20} />
						) : (
							<IconLayoutSidebarRightExpand size={20} />
						)}
					</button>
					<SidebarIcon
						icon={<IconMailQuestion size={20} />}
						tabName="approval"
						badgeCount={approvalTasks.length}
						tooltipContent={`Pending Approval (${approvalTasks.length})`}
					/>
					<SidebarIcon
						icon={<IconMessageQuestion size={20} />}
						tabName="clarification"
						badgeCount={clarificationTasks.length}
						tooltipContent={`Needs Input (${clarificationTasks.length})`}
					/>
				</div>

				{/* Content Panel */}
				<AnimatePresence>
					{isOpen && (
						<motion.div
							initial={{ opacity: 0, x: -20 }}
							animate={{ opacity: 1, x: 0 }}
							exit={{ opacity: 0, x: -20 }}
							transition={{ duration: 0.2, ease: "easeInOut" }}
							className="flex-1 overflow-y-auto custom-scrollbar p-4"
						>
							{activeTab === "approval" && (
								<div className="space-y-3">
									<h3 className="font-semibold text-lg">
										Pending Approval
									</h3>
									{approvalTasks.length > 0 ? (
										approvalTasks.map((task) => (
											<ApprovalCard
												key={task.task_id}
												task={task}
												{...handlers}
											/>
										))
									) : (
										<p className="text-sm text-neutral-500 pt-4 text-center">
											All clear!
										</p>
									)}
								</div>
							)}
						</motion.div>
					)}
				</AnimatePresence>
			</div>
		</motion.aside>
	)
}

export default ActionSidebar
