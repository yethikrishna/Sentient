// src/client/app/onboarding/page.js
"use client"
import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/utils/cn"
import toast from "react-hot-toast"
import { useRouter } from "next/navigation"

const CheckIcon = ({ className }) => (
	<svg
		xmlns="http://www.w3.org/2000/svg"
		fill="none"
		viewBox="0 0 24 24"
		strokeWidth={1.5}
		stroke="currentColor"
		className={cn("w-6 h-6 ", className)}
	>
		<path d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
	</svg>
)

const CheckFilled = ({ className }) => (
	<svg
		xmlns="http://www.w3.org/2000/svg"
		viewBox="0 0 24 24"
		fill="currentColor"
		className={cn("w-6 h-6 ", className)}
	>
		<path
			fillRule="evenodd"
			d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
			clipRule="evenodd"
		/>
	</svg>
)

const questions = [
	{ id: "user-name", question: "What is your name?", type: "text-input" },
	{
		id: "personal-interests",
		question: "What are your primary personal interests?",
		type: "multiple-choice",
		options: [
			"Reading & Literature",
			"Sports & Fitness",
			"Arts & Crafts",
			"Technology & Gadgets",
			"Travel & Exploration",
			"Cooking & Food",
			"Gaming",
			"Music & Concerts"
		]
	},
	{
		id: "professional-aspirations",
		question: "What are your professional aspirations or career goals?",
		type: "multiple-choice",
		options: [
			"Career Advancement",
			"Skill Development",
			"Entrepreneurship",
			"Work-Life Balance",
			"Innovation & Research",
			"Leadership",
			"Social Impact",
			"Financial Growth"
		]
	},
	{
		id: "political-views",
		question: "Which political ideology do you most align with?",
		type: "multiple-choice",
		options: [
			"Liberal",
			"Conservative",
			"Centrist",
			"Socialist",
			"Libertarian",
			"Anarchist",
			"Green",
			"Other / Prefer not to say"
		]
	},
	{
		id: "hobbies",
		question: "What are some of your favorite hobbies?",
		type: "multiple-choice",
		options: [
			"Hiking",
			"Photography",
			"Gardening",
			"Playing Musical Instruments",
			"Writing",
			"Painting",
			"Collecting",
			"Volunteering"
		]
	},
	{
		id: "values",
		question: "What values are most important to you?",
		type: "multiple-choice",
		options: [
			"Integrity",
			"Compassion",
			"Creativity",
			"Ambition",
			"Security",
			"Freedom",
			"Community",
			"Knowledge"
		]
	},
	{
		id: "learning-style",
		question: "How do you prefer to learn new things?",
		type: "multiple-choice",
		options: [
			"Hands-on (Kinesthetic)",
			"Visual (Seeing)",
			"Auditory (Hearing)",
			"Reading/Writing",
			"Through discussion",
			"By teaching others"
		]
	},
	{
		id: "social-preferences",
		question: "What is your preferred social setting?",
		type: "multiple-choice",
		options: [
			"Large gatherings",
			"Small intimate groups",
			"One-on-one conversations",
			"Online communities",
			"Quiet environments",
			"Loud and energetic environments"
		]
	},
	{
		id: "decision-making",
		question: "How do you typically make decisions?",
		type: "multiple-choice",
		options: [
			"Logically and analytically",
			"Intuitively and emotionally",
			"By consulting others",
			"By weighing pros and cons",
			"Quickly and decisively",
			"Slowly and deliberately"
		]
	},
	{
		id: "future-outlook",
		question: "What is your general outlook on the future?",
		type: "multiple-choice",
		options: [
			"Optimistic",
			"Pessimistic",
			"Realistic",
			"Uncertain",
			"Hopeful",
			"Anxious"
		]
	},
	{
		id: "communication-style",
		question: "What best describes your communication style?",
		type: "multiple-choice",
		options: [
			"Direct and to the point",
			"Indirect and diplomatic",
			"Expressive and open",
			"Reserved and thoughtful",
			"Assertive",
			"Passive"
		]
	}
]

const OnboardingForm = () => {
	const [currentStep, setCurrentStep] = useState(0)
	const [answers, setAnswers] = useState({})
	const [isSubmitting, setIsSubmitting] = useState(false)
	const [submissionComplete, setSubmissionComplete] = useState(false)
	const [customOptionInput, setCustomOptionInput] = useState("")
	const [showCustomInput, setShowCustomInput] = useState(false)
	const router = useRouter()

	const handleAnswer = (questionId, answer) => {
		setAnswers((prev) => {
			if (currentQuestion.type === "text-input") {
				return { ...prev, [questionId]: answer }
			} else {
				const currentAnswers = prev[questionId] || []
				if (currentAnswers.includes(answer)) {
					return {
						...prev,
						[questionId]: currentAnswers.filter(
							(item) => item !== answer
						)
					}
				} else {
					return {
						...prev,
						[questionId]: [...currentAnswers, answer]
					}
				}
			}
		})
	}

	const handleNext = () => {
		setCustomOptionInput("")
		setShowCustomInput(false)

		if (currentStep < questions.length - 1) {
			setCurrentStep((prev) => prev + 1)
		} else {
			handleSubmit()
		}
	}

	const handlePrevious = () => {
		setCustomOptionInput("")
		setShowCustomInput(false)

		if (currentStep > 0) {
			setCurrentStep((prev) => prev - 1)
		}
	}

	const handleSubmit = async () => {
		setIsSubmitting(true)
		try {
			const response = await fetch("/api/onboarding", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(answers)
			})

			const result = await response.json()
			if (!response.ok) {
				throw new Error(
					result.message || "Failed to save onboarding data"
				)
			}

			console.log("Onboarding data saved successfully.")
			setSubmissionComplete(true)
			// Redirect after a short delay
			setTimeout(() => router.push("/chat"), 2000)
		} catch (error) {
			console.error("Error saving onboarding data:", error)
			toast.error(`Error saving onboarding data: ${error.message}`)
		} finally {
			setIsSubmitting(false)
		}
	}

	const currentQuestion = questions[currentStep]

	const handleAddCustomOption = () => {
		const newOption = customOptionInput.trim()
		if (newOption) {
			const currentOptions = currentQuestion.options
			if (!currentOptions.includes(newOption)) {
				currentQuestion.options.push(newOption)
			}
			handleAnswer(currentQuestion.id, newOption)
			setCustomOptionInput("")
			setShowCustomInput(false)
		}
	}

	if (submissionComplete) {
		return (
			<div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-gray-900 to-black text-white p-4">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="text-center"
				>
					<CheckFilled className="w-24 h-24 text-green-500 mx-auto mb-6" />
					<h1 className="text-4xl font-bold mb-4">
						Onboarding Complete!
					</h1>
					<p className="text-lg text-gray-300">
						Thank you for providing your information. We're setting
						things up for you.
					</p>
					<p className="text-md text-gray-400 mt-2">
						You will be redirected shortly.
					</p>
					{/* Button to manually go to dashboard if auto-redirect is delayed or fails */}
					<button
						onClick={() => router.push("/chat")}
						className="mt-8 px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold transition-colors duration-300"
					>
						Go to Dashboard
					</button>
				</motion.div>
			</div>
		)
	}

	return (
		<div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-gray-900 to-black text-white p-4">
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5 }}
				className="w-full max-w-2xl bg-gray-800 rounded-lg shadow-xl p-8 relative"
			>
				<div className="absolute top-4 left-8 text-gray-400 text-sm">
					Step {currentStep + 1} of {questions.length}
				</div>

				<h2 className="text-3xl font-bold text-center mb-8 text-lightblue">
					Tell Us About Yourself
				</h2>

				<AnimatePresence mode="wait">
					<motion.div
						key={currentStep}
						initial={{ opacity: 0, x: 100 }}
						animate={{ opacity: 1, x: 0 }}
						exit={{ opacity: 0, x: -100 }}
						transition={{ duration: 0.3 }}
						className="mb-8"
					>
						<p className="text-xl font-semibold mb-6 text-gray-200">
							{currentQuestion.question}
						</p>
						{currentQuestion.type === "text-input" ? (
							<input
								type="text"
								value={answers[currentQuestion.id] || ""}
								onChange={(e) =>
									handleAnswer(
										currentQuestion.id,
										e.target.value
									)
								}
								className="w-full px-6 py-3 rounded-lg text-lg bg-gray-700 text-white border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
								placeholder="Type your name..."
							/>
						) : (
							<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
								{currentQuestion.options.map((option) => {
									const isSelected = (
										answers[currentQuestion.id] || []
									).includes(option)
									return (
										<button
											key={option}
											className={cn(
												"px-6 py-3 rounded-lg text-lg transition-all duration-200",
												isSelected
													? "bg-blue-600 text-white shadow-lg"
													: "bg-gray-700 text-gray-200 hover:bg-gray-600"
											)}
											onClick={() =>
												handleAnswer(
													currentQuestion.id,
													option
												)
											}
										>
											{option}
										</button>
									)
								})}
								{showCustomInput ? (
									<div className="flex items-center gap-2 md:col-span-2">
										{" "}
										{/* Span across two columns if needed */}
										<input
											type="text"
											value={customOptionInput}
											onChange={(e) =>
												setCustomOptionInput(
													e.target.value
												)
											}
											onKeyPress={(e) => {
												if (
													e.key === "Enter" &&
													customOptionInput.trim() !==
														""
												) {
													handleAddCustomOption()
												}
											}}
											className="flex-grow px-4 py-2 rounded-lg bg-gray-700 text-white border border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
											placeholder="Type your answer..."
										/>
										<button
											onClick={handleAddCustomOption}
											className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white font-semibold transition-colors duration-300"
											disabled={
												customOptionInput.trim() === ""
											}
										>
											Add
										</button>
									</div>
								) : (
									// Ensure "Other" button aligns with grid
									<button
										className={cn(
											"px-6 py-3 rounded-lg text-lg transition-all duration-200 bg-gray-700 text-gray-200 hover:bg-gray-600",
											currentQuestion.options.length %
												2 !==
												0
												? "md:col-span-2"
												: "" // Span if odd number of options
										)}
										onClick={() => setShowCustomInput(true)}
									>
										Other
									</button>
								)}
							</div>
						)}
					</motion.div>
				</AnimatePresence>

				<div className="flex justify-between mt-10">
					<button
						onClick={handlePrevious}
						disabled={currentStep === 0 || isSubmitting}
						className={cn(
							"px-6 py-3 rounded-lg text-lg font-semibold transition-colors duration-300",
							currentStep === 0 || isSubmitting
								? "bg-gray-600 text-gray-400 cursor-not-allowed"
								: "bg-gray-700 hover:bg-gray-600 text-white"
						)}
					>
						Previous
					</button>
					<button
						onClick={handleNext}
						disabled={
							(currentQuestion.type === "multiple-choice" &&
								(!answers[currentQuestion.id] ||
									answers[currentQuestion.id]?.length ===
										0) && // Check if undefined or empty
								!showCustomInput) ||
							(currentQuestion.type === "text-input" &&
								!answers[currentQuestion.id]) ||
							isSubmitting
						}
						className={cn(
							"px-6 py-3 rounded-lg text-lg font-semibold transition-colors duration-300",
							// Disable if no answer for current question (text or multiple choice)
							!answers[currentQuestion.id] ||
								(currentQuestion.type === "multiple-choice" &&
									answers[currentQuestion.id]?.length === 0 &&
									!showCustomInput) ||
								isSubmitting
								? "bg-blue-800 text-blue-300 cursor-not-allowed"
								: "bg-blue-600 hover:bg-blue-700 text-white"
						)}
					>
						{isSubmitting
							? "Submitting..."
							: currentStep === questions.length - 1
								? "Finish"
								: "Next"}
					</button>
				</div>
			</motion.div>
		</div>
	)
}

export default OnboardingForm
