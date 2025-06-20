"use client"
import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/utils/cn"
import toast from "react-hot-toast"
import { useRouter } from "next/navigation"
import { IconLoader } from "@tabler/icons-react"

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
		id: "timezone",
		question: "What is your timezone?",
		type: "select",
		options: [
			{ value: "America/New_York", label: "Eastern Time (US & Canada)" },
			{ value: "America/Chicago", label: "Central Time (US & Canada)" },
			{ value: "America/Denver", label: "Mountain Time (US & Canada)" },
			{ value: "America/Phoenix", label: "Arizona" },
			{
				value: "America/Los_Angeles",
				label: "Pacific Time (US & Canada)"
			},
			{ value: "America/Anchorage", label: "Alaska" },
			{ value: "Pacific/Honolulu", label: "Hawaii" },
			{ value: "Europe/London", label: "London, Dublin (GMT/BST)" },
			{ value: "Europe/Berlin", label: "Berlin, Paris (CET)" },
			{ value: "Europe/Moscow", label: "Moscow (MSK)" },
			{ value: "Asia/Dubai", label: "Dubai (GST)" },
			{ value: "Asia/Kolkata", label: "India (IST)" },
			{ value: "Asia/Singapore", label: "Singapore (SGT)" },
			{ value: "Asia/Tokyo", label: "Tokyo (JST)" },
			{ value: "Australia/Sydney", label: "Sydney (AEST)" },
			{ value: "UTC", label: "Coordinated Universal Time (UTC)" }
		]
	},
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
	const [answers, setAnswers] = useState({})
	const [isSubmitting, setIsSubmitting] = useState(false)
	const [submissionComplete, setSubmissionComplete] = useState(false)
	const router = useRouter()
	const [isLoading, setIsLoading] = useState(true) // Check onboarding status on load
	const [customInputs, setCustomInputs] = useState({})
	const [showCustomInputs, setShowCustomInputs] = useState({})

	useEffect(() => {
		const checkOnboardingStatus = async () => {
			try {
				const response = await fetch("/api/user/data")
				if (!response.ok) {
					throw new Error("Could not fetch user data.")
				}
				const result = await response.json()
				if (result?.data?.onboardingComplete) {
					router.push("/chat") // User already onboarded, redirect
				} else {
					setIsLoading(false) // Not onboarded, show the form
				}
			} catch (error) {
				toast.error(error.message)
				setIsLoading(false) // On error, allow user to proceed
			}
		}
		checkOnboardingStatus()
	}, [router])

	const handleAnswer = (questionId, answer, isTextInput = false) => {
		setAnswers((prev) => {
			if (isTextInput) {
				return { ...prev, [questionId]: answer }
			}
			// For multiple choice
			const currentAnswers = prev[questionId] || []
			const newAnswers = currentAnswers.includes(answer)
				? currentAnswers.filter((item) => item !== answer) // Deselect
				: [...currentAnswers, answer] // Select
			return { ...prev, [questionId]: newAnswers }
		})
	}

	const handleCustomInputChange = (questionId, value) => {
		setCustomInputs((prev) => ({ ...prev, [questionId]: value }))
	}

	const toggleCustomInput = (questionId) => {
		setShowCustomInputs((prev) => ({
			...prev,
			[questionId]: !prev[questionId]
		}))
	}

	const handleAddCustomOption = (questionId) => {
		const newOption = customInputs[questionId]?.trim()
		if (newOption) {
			handleAnswer(questionId, newOption, false)
			handleCustomInputChange(questionId, "") // Clear input
			toggleCustomInput(questionId) // Hide input
		}
	}

	const handleSubmit = async (e) => {
		e.preventDefault() // Prevent form from reloading the page
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

	if (isLoading) {
		return (
			<div className="flex flex-col items-center justify-center min-h-screen bg-matteblack text-white">
				<IconLoader className="w-10 h-10 animate-spin text-lightblue" />
			</div>
		)
	}
	if (submissionComplete) {
		return (
			<div className="flex flex-col items-center justify-center min-h-screen bg-matteblack text-white p-4">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="text-center"
				>
					<CheckFilled className="w-24 h-24 text-green-500 mx-auto mb-6" />
					<h1 className="text-4xl font-Poppins font-bold mb-4">
						Onboarding Complete!
					</h1>
					<p className="text-lg text-gray-300">
						Thank you. We're setting things up for you.
					</p>
					<p className="text-md text-gray-400 mt-2">
						Redirecting to your new companion...
					</p>
				</motion.div>
			</div>
		)
	}

	return (
		<div className="min-h-screen bg-matteblack text-white p-6 flex items-center justify-center">
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5 }}
				className="w-full max-w-4xl"
			>
				<div className="text-center mb-12">
					<h1 className="text-4xl font-Poppins font-bold mb-3 text-white">
						Welcome to Sentient
					</h1>
					<p className="text-lg text-gray-400">
						Let's personalize your AI companion.
					</p>
				</div>

				<form onSubmit={handleSubmit} className="space-y-10">
					{questions.map((q) => {
						const selectedAnswers = answers[q.id] || []
						const customAnswers = Array.isArray(selectedAnswers)
							? selectedAnswers.filter(
									(ans) =>
										!q.options?.some((o) =>
											typeof o === "object"
												? o.value === ans
												: o === ans
										)
								)
							: []

						return (
							<div key={q.id}>
								<label className="block text-xl font-Poppins font-semibold mb-4 text-gray-200">
									{q.question}
								</label>
								{q.type === "text-input" ? (
									<input
										type="text"
										value={answers[q.id] || ""}
										onChange={(e) =>
											handleAnswer(
												q.id,
												e.target.value,
												true
											)
										}
										className="w-full px-4 py-3 rounded-lg bg-neutral-800 text-white border border-neutral-700 focus:outline-none focus:ring-2 focus:ring-lightblue placeholder-gray-500"
										placeholder="Type your answer here..."
										required={q.id === "user-name"}
									/>
								) : q.type === "select" ? (
									<select
										value={answers[q.id] || ""}
										onChange={(e) =>
											handleAnswer(
												q.id,
												e.target.value,
												true
											)
										}
										className="w-full px-4 py-3 rounded-lg bg-neutral-800 text-white border border-neutral-700 focus:outline-none focus:ring-2 focus:ring-lightblue"
										required={q.id === "timezone"}
									>
										<option value="" disabled>
											Select your timezone...
										</option>
										{q.options.map((option) => (
											<option
												key={option.value}
												value={option.value}
											>
												{option.label}
											</option>
										))}
									</select>
								) : (
									<div className="flex flex-wrap gap-3">
										{q.options.map((option) => {
											const isSelected =
												selectedAnswers.includes(option)
											return (
												<button
													key={option}
													type="button"
													className={cn(
														"px-5 py-2.5 rounded-lg text-base font-medium transition-all duration-200",
														isSelected
															? "bg-lightblue text-white shadow-md"
															: "bg-neutral-700 text-gray-300 hover:bg-neutral-600"
													)}
													onClick={() =>
														handleAnswer(
															q.id,
															option,
															false
														)
													}
												>
													{option}
												</button>
											)
										})}
										{customAnswers.map((ans) => (
											<button
												key={ans}
												type="button"
												className="px-5 py-2.5 rounded-lg text-base font-medium transition-all duration-200 bg-lightblue text-white shadow-md"
												onClick={() =>
													handleAnswer(
														q.id,
														ans,
														false
													)
												}
											>
												{ans}
											</button>
										))}
										<button
											type="button"
											className={cn(
												"px-5 py-2.5 rounded-lg text-base font-medium transition-all duration-200 bg-neutral-700 text-gray-300 hover:bg-neutral-600"
											)}
											onClick={() =>
												toggleCustomInput(q.id)
											}
										>
											Other...
										</button>
									</div>
								)}
								{showCustomInputs[q.id] && (
									<div className="flex items-center gap-2 mt-3">
										<input
											type="text"
											value={customInputs[q.id] || ""}
											onChange={(e) =>
												handleCustomInputChange(
													q.id,
													e.target.value
												)
											}
											onKeyPress={(e) => {
												if (e.key === "Enter") {
													e.preventDefault()
													handleAddCustomOption(q.id)
												}
											}}
											className="flex-grow px-4 py-2 rounded-lg bg-neutral-800 text-white border border-neutral-700 focus:outline-none focus:ring-2 focus:ring-lightblue"
											placeholder="Type your answer..."
										/>
										<button
											type="button"
											onClick={() =>
												handleAddCustomOption(q.id)
											}
											className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white font-semibold transition-colors duration-300"
											disabled={
												!customInputs[q.id]?.trim()
											}
										>
											Add
										</button>
									</div>
								)}
							</div>
						)
					})}
					<div className="flex justify-end pt-6 border-t border-neutral-700">
						<button
							type="submit"
							disabled={
								!answers["user-name"]?.trim() ||
								isSubmitting ||
								!answers["timezone"]
							}
							className="px-8 py-3 rounded-lg text-lg font-semibold transition-colors duration-300 bg-lightblue hover:bg-blue-700 text-white disabled:bg-neutral-600 disabled:text-gray-400 disabled:cursor-not-allowed"
						>
							{isSubmitting ? "Saving..." : "Save & Continue"}
						</button>
					</div>
				</form>
			</motion.div>
		</div>
	)
}

export default OnboardingForm
