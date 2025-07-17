"use client"

import React, { useState } from "react"
import toast from "react-hot-toast"

const ClarificationCard = ({ task, onSubmitAnswers }) => {
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
		await onSubmitAnswers(task.task_id, answersPayload)
		setIsSubmitting(false)
	}

	return (
		<div className="bg-neutral-800/50 p-3 rounded-lg space-y-3 border border-dashed border-blue-500/50">
			<p className="font-semibold text-sm text-white">
				{task.description}
			</p>
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
							rows={1}
							className="w-full p-2 bg-neutral-700/80 border border-neutral-600 rounded-md text-sm focus:border-blue-500 transition-colors"
							placeholder="Your answer..."
						/>
					</div>
				))}
			</div>
			<div className="flex justify-end">
				<button
					onClick={handleSubmit}
					disabled={isSubmitting}
					className="px-3 py-1 text-xs font-semibold bg-blue-600 text-white rounded-md hover:bg-blue-500 disabled:opacity-50"
				>
					{isSubmitting ? "Submitting..." : "Submit Answers"}
				</button>
			</div>
		</div>
	)
}

export default ClarificationCard
