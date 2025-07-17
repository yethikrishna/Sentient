// A new file: src/client/components/organizer/TaskBlock.js
"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import {
	IconLoader,
	IconCircleCheck,
	IconMailQuestion,
	IconAlertTriangle,
	IconPencil,
	IconTrash,
	IconRefresh,
	IconMessageQuestion,
	IconClock,
	IconPlayerPlay,
	IconHelpCircle,
	IconX
} from "@tabler/icons-react"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"

const statusMap = {
	planning: {
		icon: IconRefresh,
		color: "text-blue-400",
		label: "Planning..."
	},
	pending: { icon: IconClock, color: "text-yellow-400", label: "Pending" },
	processing: {
		icon: IconPlayerPlay,
		color: "text-blue-400",
		label: "In Progress"
	},
	completed: {
		icon: IconCircleCheck,
		color: "text-green-400",
		label: "Completed"
	},
	error: { icon: IconAlertTriangle, color: "text-red-400", label: "Error" },
	approval_pending: {
		icon: IconMailQuestion,
		color: "text-purple-400",
		label: "Approve Plan"
	},
	clarification_pending: {
		icon: IconMessageQuestion,
		color: "text-orange-400",
		label: "Needs Info"
	},
	cancelled: { icon: IconX, color: "text-gray-500", label: "Cancelled" },
	default: { icon: IconHelpCircle, color: "text-gray-400", label: "Unknown" }
}

const AnswerInput = ({ question, onAnswer }) => {
	const [answer, setAnswer] = useState("")

	const handleSubmit = (e) => {
		e.preventDefault()
		if (answer.trim()) {
			onAnswer(question.question_id, answer)
			setAnswer("")
		}
	}

	return (
		<form onSubmit={handleSubmit} className="mt-2 flex gap-2">
			<input
				type="text"
				value={answer}
				onChange={(e) => setAnswer(e.target.value)}
				placeholder={`Answer: ${question.text}`}
				className="flex-grow bg-neutral-700/50 border border-neutral-600 rounded-md px-2 py-1 text-xs text-white placeholder-gray-400 focus:ring-1 focus:ring-[var(--color-accent-blue)]"
			/>
			<button
				type="submit"
				className="text-xs text-[var(--color-accent-blue)] hover:underline"
			>
				Send
			</button>
		</form>
	)
}

const TaskBlock = ({
	task,
	onDelete,
	onApprove,
	onViewDetails,
	onAnswerClarification,
	onEdit
}) => {
	const statusInfo = statusMap[task.status] || statusMap.default

	const handleAnswer = (questionId, answerText) => {
		onAnswerClarification(task.task_id, [
			{ question_id: questionId, answer_text: answerText }
		])
	}

	const handleApproveClick = (e) => {
		e.stopPropagation()
		if (task.plan && task.plan.length > 0) {
			onApprove(task.task_id)
		} else {
			toast.error("Cannot approve: The plan has not been generated yet.")
		}
	}

	const handleDisapproveClick = (e) => {
		e.stopPropagation()
		onDelete(task.task_id)
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, scale: 0.95 }}
			whileHover={{
				y: -2,
				z: 5,
				boxShadow: "0 10px 20px rgba(0,0,0,0.3)"
			}}
			className="bg-neutral-800/80 p-3 rounded-lg border border-neutral-700/80 cursor-pointer group"
			onClick={() => onViewDetails(task)}
		>
			<div className="flex justify-between items-start">
				<p className="text-sm text-neutral-100 flex-grow pr-2">
					{task.description}
				</p>
				<div
					className={cn(
						"flex items-center gap-1 text-xs font-semibold flex-shrink-0",
						statusInfo.color
					)}
				>
					<statusInfo.icon size={14} />
					<span>{statusInfo.label}</span>
				</div>
			</div>

			{task.status === "clarification_pending" &&
				task.clarifying_questions && (
					<div className="mt-3 space-y-2">
						{task.clarifying_questions.map((q) => (
							<AnswerInput
								key={q.question_id}
								question={q}
								onAnswer={handleAnswer}
							/>
						))}
					</div>
				)}

			{task.status === "approval_pending" && (
				<div className="mt-3 flex gap-2">
					<button
						onClick={handleApproveClick}
						className="flex-1 text-xs py-1.5 px-2 rounded-md bg-green-500/20 text-green-300 hover:bg-green-500/40"
					>
						Approve
					</button>
					<button
						onClick={handleDisapproveClick}
						className="flex-1 text-xs py-1.5 px-2 rounded-md bg-red-500/20 text-red-300 hover:bg-red-500/40"
					>
						Disapprove
					</button>
				</div>
			)}

			<div className="absolute bottom-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
				<button
					onClick={(e) => {
						e.stopPropagation()
						onEdit(task)
					}}
					className="p-1 rounded-full bg-neutral-700/50 hover:bg-[var(--color-accent-orange)]"
				>
					<IconPencil size={12} />
				</button>
				<button
					onClick={handleDisapproveClick}
					className="p-1 rounded-full bg-neutral-700/50 hover:bg-[var(--color-accent-red)]"
				>
					<IconTrash size={12} />
				</button>
			</div>
		</motion.div>
	)
}

export default TaskBlock
