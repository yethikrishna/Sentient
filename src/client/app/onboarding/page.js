"use client"
import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@utils/cn"
import toast from "react-hot-toast"
import { useRouter } from "next/navigation"
import { IconLoader, IconMapPin, IconMapPinFilled } from "@tabler/icons-react"

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
	{
		id: "user-name",
		question: "What should I call you?",
		type: "text-input",
		required: true
	},
	{
		id: "timezone",
		question: "What is your timezone?",
		type: "select",
		required: true,
		options: [
			{ value: "America/New_York", label: "Eastern Time (US & Canada)" },
			{ value: "America/Chicago", label: "Central Time (US & Canada)" },
			{ value: "America/Denver", label: "Mountain Time (US & Canada)" },
			{
				value: "America/Los_Angeles",
				label: "Pacific Time (US & Canada)"
			},
			{ value: "Europe/London", label: "London, Dublin (GMT/BST)" },
			{ value: "Europe/Berlin", label: "Berlin, Paris (CET)" },
			{ value: "Asia/Kolkata", label: "India (IST)" },
			{ value: "Asia/Singapore", label: "Singapore (SGT)" },
			{ value: "UTC", label: "Coordinated Universal Time (UTC)" }
		]
	},
	{
		id: "location",
		question: "Where are you located?",
		description:
			"Your location helps me provide relevant info like local weather and places. You can skip this if you're not comfortable sharing.",
		type: "location-input"
	},
	{
		id: "professional-context",
		question:
			"To help me assist you better, what do you do for work and what are your main goals?",
		type: "textarea",
		placeholder:
			"e.g., I'm a software developer aiming to become a team lead. I want to improve my project management skills."
	},
	{
		id: "personal-context",
		question: "What are some of your hobbies or personal interests?",
		type: "textarea",
		placeholder:
			"e.g., I enjoy hiking on weekends, I'm learning to play the guitar, and I follow European soccer."
	}
]

const OnboardingForm = () => {
	const [answers, setAnswers] = useState({})
	const [isSubmitting, setIsSubmitting] = useState(false)
	const [submissionComplete, setSubmissionComplete] = useState(false)
	const router = useRouter()
	const [isLoading, setIsLoading] = useState(true) // Check onboarding status on load
	const [locationState, setLocationState] = useState({
		loading: false,
		data: null,
		error: null
	})

	useEffect(() => {
		const checkOnboardingStatus = async () => {
			try {
				const response = await fetch("/api/user/data")
				if (!response.ok) {
					throw new Error("Could not fetch user data.")
				}
				const result = await response.json()
				if (result?.data?.onboardingComplete) {
					router.push("/home") // User already onboarded, redirect
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
			return { ...prev, [questionId]: answer }
		})
	}

	const handleGetLocation = () => {
		if (navigator.geolocation) {
			setLocationState({ loading: true, data: null, error: null })
			navigator.geolocation.getCurrentPosition(
				(position) => {
					const { latitude, longitude } = position.coords
					const locationData = { latitude, longitude }
					setLocationState({
						loading: false,
						data: locationData,
						error: null
					})
					handleAnswer("location", locationData, true)
				},
				(error) => {
					setLocationState({
						loading: false,
						data: null,
						error: error.message
					})
					toast.error(`Could not get location: ${error.message}`)
				}
			)
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
			setTimeout(() => router.push("/home"), 2000)
		} catch (error) {
			console.error("Error saving onboarding data:", error)
			toast.error(`Error saving onboarding data: ${error.message}`)
		} finally {
			setIsSubmitting(false)
		}
	}

	if (isLoading) {
		return (
			<div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)]">
				<IconLoader className="w-10 h-10 animate-spin text-[var(--color-accent-blue)]" />
			</div>
		)
	}
	if (submissionComplete) {
		return (
			<div className="flex flex-col items-center justify-center min-h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] p-4">
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ duration: 0.5 }}
					className="text-center"
				>
					<CheckFilled className="w-24 h-24 text-[var(--color-accent-green)] mx-auto mb-6" />
					<h1 className="text-4xl font-Poppins font-bold mb-4">
						Onboarding Complete!
					</h1>
					<p className="text-lg text-[var(--color-text-secondary)]">
						Thank you. We're setting things up for you.
					</p>
					<p className="text-md text-[var(--color-text-muted)] mt-2">
						Redirecting to your new companion...
					</p>
				</motion.div>
			</div>
		)
	}

	return (
		<div className="min-h-screen bg-[var(--color-primary-background)] text-[var(--color-text-primary)] p-4 sm:p-6 flex items-center justify-center">
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				transition={{ duration: 0.5 }}
				className="w-full max-w-4xl mx-auto"
			>
				<div className="text-center mb-12">
					<h1 className="text-3xl sm:text-4xl font-Poppins font-bold mb-3 text-[var(--color-text-primary)]">
						Welcome to Sentient
					</h1>
					<p className="text-lg text-[var(--color-text-secondary)]">
						Let's personalize your AI companion.
					</p>
				</div>

				<form onSubmit={handleSubmit} className="space-y-10">
					{questions.map((q) => {
						return (
							<div key={q.id}>
								<label className="block text-lg sm:text-xl font-Poppins font-semibold mb-2 text-[var(--color-text-primary)]">
									{q.question}
								</label>
								{q.description && (
									<p className="text-sm text-[var(--color-text-secondary)] mb-4">
										{q.description}
									</p>
								)}
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
										className="w-full px-4 py-3 rounded-lg bg-[var(--color-primary-surface)] text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)] placeholder-[var(--color-text-muted)]"
										placeholder="Type your answer here..."
										required={q.required}
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
										className="w-full px-4 py-3 rounded-lg bg-[var(--color-primary-surface)] text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)]"
										required={q.required}
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
								) : q.type === "textarea" ? (
									<textarea
										value={answers[q.id] || ""}
										onChange={(e) =>
											handleAnswer(
												q.id,
												e.target.value,
												true
											)
										}
										className="w-full px-4 py-3 rounded-lg bg-[var(--color-primary-surface)] text-[var(--color-text-primary)] border border-[var(--color-primary-surface-elevated)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-blue)] placeholder-[var(--color-text-muted)] min-h-[100px] resize-y"
										placeholder={q.placeholder}
									/>
								) : q.type === "location-input" ? (
									<div className="flex items-center gap-4">
										<button
											type="button"
											onClick={handleGetLocation}
											disabled={locationState.loading}
											className="flex items-center gap-2 px-5 py-3 rounded-lg bg-[var(--color-primary-surface-elevated)] text-[var(--color-text-primary)] hover:bg-neutral-600 transition-colors"
										>
											<IconMapPin size={20} />
											<span>
												{locationState.loading
													? "Getting Location..."
													: "Share Current Location"}
											</span>
										</button>
										{locationState.data && (
											<div className="flex items-center gap-2 text-[var(--color-accent-green)]">
												<IconMapPinFilled size={20} />
												<span>Location captured!</span>
											</div>
										)}
										{locationState.error && (
											<p className="text-sm text-[var(--color-accent-red)]">
												Could not get location. You can
												continue without it.
											</p>
										)}
									</div>
								) : null}
							</div>
						)
					})}
					<div className="flex justify-end pt-6 border-t border-[var(--color-primary-surface-elevated)]">
						<button
							type="submit"
							disabled={
								!answers["user-name"]?.trim() ||
								isSubmitting ||
								!answers["timezone"]
							}
							className="px-8 py-3 rounded-lg text-lg font-semibold transition-colors duration-300 bg-[var(--color-accent-blue)] hover:bg-blue-700 text-white disabled:bg-neutral-600 disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
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
