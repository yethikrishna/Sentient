"use client"

import { AnimatePresence, motion } from "framer-motion"
import { IconAlignBoxLeftMiddleFilled, IconCalendar } from "@tabler/icons-react"

const tabs = [
	{
		title: "List",
		value: "list",
		icon: <IconAlignBoxLeftMiddleFilled size={18} />
	},
	{ title: "Calendar", value: "calendar", icon: <IconCalendar size={18} /> }
]

const buttonVariants = {
	initial: {
		gap: 0,
		paddingLeft: ".5rem",
		paddingRight: ".5rem"
	},
	animate: (selected) => ({
		gap: selected ? ".5rem" : 0,
		paddingLeft: selected ? "1rem" : ".5rem",
		paddingRight: selected ? "1rem" : ".5rem"
	})
}

const spanVariants = {
	initial: { width: 0, opacity: 0 },
	animate: { width: "auto", opacity: 1 },
	exit: { width: 0, opacity: 0 }
}

const transition = { delay: 0.1, type: "spring", bounce: 0, duration: 0.35 }

const Tab = ({ text, selected, setSelected, value, children }) => {
	return (
		<motion.button
			variants={buttonVariants}
			initial="initial"
			animate="animate"
			custom={selected}
			onClick={() => setSelected(value)}
			transition={transition}
			className={`${
				selected ? "bg-white/10 text-white " : " hover:text-white"
			} relative flex items-center rounded-full px-4 py-2 text-base font-medium text-neutral-400 transition-colors duration-300`}
		>
			{children}
			<AnimatePresence>
				{selected && (
					<motion.span
						variants={spanVariants}
						initial="initial"
						animate="animate"
						exit="exit"
						transition={transition}
						className="overflow-hidden"
					>
						{text}
					</motion.span>
				)}
			</AnimatePresence>
		</motion.button>
	)
}

const TaskViewSwitcher = ({ view, setView }) => {
	return (
		<div className={"flex flex-wrap items-center gap-2"}>
			{tabs.map((tab) => (
				<Tab
					text={tab.title}
					selected={view === tab.value}
					setSelected={setView}
					value={tab.value}
					key={tab.value}
				>
					{tab.icon}
				</Tab>
			))}
		</div>
	)
}

export default TaskViewSwitcher
