"use client"

import React, { useState } from "react"
import { motion } from "framer-motion"
import toast from "react-hot-toast"
import { IconLoader } from "@tabler/icons-react"

const ClarificationCard = ({ task, onAnswerClarifications }) => {
	const [answers, setAnswers] = useState({})
	const [isSubmitting, setIsSubmitting] = useState(false)

	const handleAnswerChange = (questionId, text) => {
		setAnswers((prev) => ({ ...prev, [questionId]: text }))
	}

	const handleSubmit = async () => {
		const unansweredQuestions = task.clarifying_questions.filter(
			(q) => !answers[q.question_id]?.trim()
		)
		if (unansweredQuestions.length > 0) {
			toast.error("Please answer all questions before submitting.")
			return
		}

		setIsSubmitting(true)
		const answersPayload = Object.entries(answers).map(
			([question_id, answer_text]) => ({
				question_id,
				answer_text
			})
		)
		await onAnswerClarifications(task.task_id, answersPayload)
		setIsSubmitting(false)
	}

	return (
		<motion.div
			layout
			initial={{ opacity: 0, y: 10 }}
			animate={{ opacity: 1, y: 0 }}
			exit={{ opacity: 0, x: -20 }}
			className="bg-dark-surface/70 p-4 rounded-lg space-y-3 border border-dark-surface-elevated hover:border-sentient-blue/50 transition-colors"
		>
			<p className="font-medium text-sm text-white">{task.name}</p>
			<div className="space-y-2">
				{task.clarifying_questions.map((q) => (
					<div key={q.question_id}>
						<label className="text-xs text-gray-400 block mb-1">
							{q.text}
						</label>
						<textarea
							value={answers[q.question_id] || ""}
							onChange={(e) =>
								handleAnswerChange(
									q.question_id,
									e.target.value
								)
							}
							rows={2}
							className="w-full p-2 bg-dark-bg border border-dark-surface-elevated rounded-md text-sm transition-colors focus:border-sentient-blue focus:ring-0"
							placeholder="Your answer..."
						/>
					</div>
				))}
			</div>
			<div className="flex justify-end">
				<button
					onClick={handleSubmit}
					disabled={isSubmitting}
					className="px-3 py-1.5 text-xs font-semibold bg-sentient-blue text-white rounded-md hover:bg-sentient-blue-dark disabled:opacity-50 flex items-center gap-2"
				>
					{isSubmitting && (
						<IconLoader size={14} className="animate-spin" />
					)}
					{isSubmitting ? "Submitting..." : "Submit Answers"}
				</button>
			</div>
		</motion.div>
	)
}

export default ClarificationCard
