"use client"
import React, { useMemo } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { IconSearch, IconChevronDown } from "@tabler/icons-react"
import { groupTasksByDate } from "@utils/taskUtils"
import TaskCardList from "./TaskCardList"
import CollapsibleSection from "./CollapsibleSection"
import { startOfDay, isBefore } from "date-fns"

const ListView = ({
	oneTimeTasks,
	recurringTasks,
	onSelectTask,
	searchQuery,
	onSearchChange
}) => {
	const { today, tomorrow, future } = groupTasksByDate(oneTimeTasks)

	const containerVariants = {
		hidden: { opacity: 1 }, // Let the parent control opacity
		visible: {
			opacity: 1,
			transition: { staggerChildren: 0.07 }
		}
	}

	const sections = [
		{ title: "Today", tasks: today },
		{ title: "Tomorrow", tasks: tomorrow },
		{ title: "Future", tasks: future }
	]

	const upcomingTasksCount =
		recurringTasks.length + today.length + tomorrow.length + future.length

	if (upcomingTasksCount === 0 && !searchQuery) {
		return (
			<div className="flex flex-col items-center justify-center h-full text-center text-neutral-500 p-8">
				<div className="max-w-md">
					<h3 className="text-xl font-semibold text-neutral-300 mb-2">
						Your Task List is Empty
					</h3>
					<p className="mb-4">
						Use the input box below to add your first task. You can
						add as many as you want—they'll all be executed in
						parallel.
					</p>
					<p className="text-sm">
						Sentient will create a plan and may ask for your
						approval or for more details if needed.
					</p>
				</div>
			</div>
		)
	}

	return (
		<div className="p-6 space-y-4 overflow-y-auto custom-scrollbar h-full bg-brand-black/50 backdrop-blur-sm rounded-xl border border-zinc-700/50">
			<div className="relative">
				<IconSearch
					className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500"
					size={20}
				/>
				<input
					type="text"
					value={searchQuery}
					onChange={(e) => onSearchChange(e.target.value)}
					placeholder="Search tasks..."
					className="w-full bg-neutral-900 border border-neutral-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder-neutral-500 focus:ring-2 focus:ring-sentient-blue"
				/>
			</div>

			<AnimatePresence>
				<div className="divide-y divide-zinc-700">
					{recurringTasks.length > 0 && (
						<CollapsibleSection
							key="recurring"
							title={`Active Workflows (${recurringTasks.length})`}
							defaultOpen={true}
						>
							<motion.div
								className="space-y-3 pt-2"
								variants={containerVariants}
								initial="hidden"
								animate="visible"
							>
								{recurringTasks.map((task) => (
									<TaskCardList
										key={task.task_id}
										task={task}
										onSelectTask={onSelectTask}
									/>
								))}
							</motion.div>
						</CollapsibleSection>
					)}

					{sections.map(
						(section) =>
							section.tasks.length > 0 && (
								<CollapsibleSection
									key={section.title}
									title={`${section.title} (${section.tasks.length})`}
									defaultOpen={true}
								>
									<motion.div
										className="space-y-3 pt-2"
										variants={containerVariants}
										initial="hidden"
										animate="visible"
									>
										{section.tasks.map((task) => (
											<TaskCardList
												key={task.instance_id}
												task={task}
												onSelectTask={onSelectTask}
											/>
										))}
									</motion.div>
								</CollapsibleSection>
							)
					)}
				</div>
			</AnimatePresence>
		</div>
	)
}

export default ListView
